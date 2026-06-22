from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent, PerformanceSnapshot


class DegradationMode(str, Enum):
    BEHAVIORAL_DRIFT = "behavioral_drift"
    INPUT_BRITTLENESS = "input_brittleness"
    ALIGNMENT_CREEP = "alignment_creep"
    TOOL_MISUSE = "tool_misuse"


@dataclass
class DegradationState:
    mode: DegradationMode
    intensity: float        # 0.0 – 1.0
    tick_started: int
    active: bool = True
    ticks_elapsed: int = 0


class DegradationEngine:
    def __init__(self, agent: "BaseAgent") -> None:
        self.agent = agent
        self._tick: int = 0
        self._active: list[DegradationState] = []

        # Store baseline from contract so we can always reset cleanly
        self._baseline = dict(agent.contract.metrics)

        # Disaggregated task completion by input category (for INPUT_BRITTLENESS)
        self._category_rates: dict[str, float] = {
            surface: self._baseline["task_completion_rate"]
            for surface in agent.contract.task_surface
        }

        # Extra metric not in PerformanceSnapshot, tracked separately
        self._brand_violation_flag_rate: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def inject(self, mode: DegradationMode, intensity: float = 0.5) -> None:
        self._active.append(DegradationState(
            mode=mode,
            intensity=max(0.0, min(1.0, intensity)),
            tick_started=self._tick,
        ))

    def resolve(self, mode: DegradationMode) -> None:
        """Remove all active degradations of a given mode (e.g. after intervention)."""
        self._active = [d for d in self._active if d.mode != mode]

    def tick(self) -> "PerformanceSnapshot":
        from ..agents.base_agent import PerformanceSnapshot

        self._tick += 1
        for state in self._active:
            state.ticks_elapsed += 1

        metrics = dict(self._baseline)
        notes: list[str] = []

        for state in self._active:
            if not state.active:
                continue
            t = state.ticks_elapsed
            i = state.intensity

            if state.mode == DegradationMode.BEHAVIORAL_DRIFT:
                # Slow start, accelerates after tick 5 — simulates stale RAG index
                ramp = t / 5.0 if t <= 5 else 1.0 + (t - 5) * 0.3
                delta = i * ramp * 0.01
                metrics["policy_citation_error_rate"] = min(
                    1.0, metrics["policy_citation_error_rate"] + delta
                )
                metrics["hallucination_rate"] = min(
                    1.0, metrics["hallucination_rate"] + delta * 0.8
                )
                notes.append(f"behavioral_drift t={t}")

            elif state.mode == DegradationMode.INPUT_BRITTLENESS:
                # Drops "billing_dispute" completion sharply; overall looks fine
                target_category = "billing_dispute"
                drop = min(0.6, i * t * 0.05)
                self._category_rates[target_category] = max(
                    0.0, self._baseline["task_completion_rate"] - drop
                )
                # Overall rate is weighted average — hidden by other categories
                n = len(self._category_rates)
                metrics["task_completion_rate"] = sum(
                    self._category_rates.values()
                ) / n
                notes.append(f"input_brittleness billing_dispute drop={drop:.3f}")

            elif state.mode == DegradationMode.ALIGNMENT_CREEP:
                # Slow CSAT drift + brand violation; stays below absolute threshold for a while
                drift_per_tick = i * 0.015
                metrics["csat_score"] = max(
                    0.0, metrics["csat_score"] - drift_per_tick * t
                )
                self._brand_violation_flag_rate = min(1.0, i * t * 0.008)
                notes.append(
                    f"alignment_creep csat_drift={drift_per_tick * t:.3f} "
                    f"brand_violation={self._brand_violation_flag_rate:.3f}"
                )

            elif state.mode == DegradationMode.TOOL_MISUSE:
                # Sudden spike — simulates tool schema change
                spike = min(1.0, i * (1.0 + t * 0.1))
                metrics["tool_misuse_rate"] = min(
                    1.0, metrics["tool_misuse_rate"] + spike * 0.03
                )
                # CSAT and task_completion intentionally unaffected early on
                notes.append(f"tool_misuse spike={spike:.3f}")

        snapshot = PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            task_completion_rate=metrics["task_completion_rate"],
            csat_score=metrics["csat_score"],
            policy_citation_error_rate=metrics["policy_citation_error_rate"],
            tool_misuse_rate=metrics["tool_misuse_rate"],
            hallucination_rate=metrics["hallucination_rate"],
            notes="; ".join(notes),
        )
        self.agent.record_snapshot(snapshot)
        return snapshot

    def get_disaggregated_metrics(self) -> dict[str, float]:
        """Reveals per-category task completion — exposes INPUT_BRITTLENESS failures."""
        return dict(self._category_rates)

    def reset(self) -> None:
        self._tick = 0
        self._active.clear()
        self._category_rates = {
            surface: self._baseline["task_completion_rate"]
            for surface in self.agent.contract.task_surface
        }
        self._brand_violation_flag_rate = 0.0
        self.agent._snapshots.clear()

    @property
    def current_tick(self) -> int:
        return self._tick

    @property
    def brand_violation_flag_rate(self) -> float:
        return self._brand_violation_flag_rate
