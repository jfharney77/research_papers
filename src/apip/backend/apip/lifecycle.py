from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import TYPE_CHECKING

from ..agents.base_agent import PerformanceSnapshot, TriggerEvent, _HIGHER_IS_WORSE
from .schema import (
    APIP,
    APIPPhase,
    CauseAttributionReport,
    CheckIn,
    ExitOutcome,
    FailureMode,
    InterventionPlan,
    InterventionStep,
    InterventionTier,
)

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent

_DATA_PATH = Path(__file__).parent.parent / "data" / "apips.json"


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (APIPPhase, FailureMode, InterventionTier)):
        return obj.value
    raise TypeError(f"Unserializable: {type(obj)}")


def _load_apips() -> dict[str, dict]:
    if _DATA_PATH.exists():
        with open(_DATA_PATH) as f:
            return json.load(f)
    return {}


def _save_apips(records: dict[str, dict]) -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_DATA_PATH, "w") as f:
        json.dump(records, f, default=_serialize, indent=2)


class APIPLifecycle:

    # ------------------------------------------------------------------
    # Phase 1 — Trigger
    # ------------------------------------------------------------------

    @staticmethod
    def check_trigger(agent: "BaseAgent") -> APIP | None:
        events: list[TriggerEvent] = agent.evaluate_against_contract()
        if not events:
            return None

        record = APIP(
            agent_id=agent.agent_id,
            phase=APIPPhase.TRIGGER,
            trigger_events=[
                {
                    "metric_name": e.metric_name,
                    "observed_value": e.observed_value,
                    "threshold_value": e.threshold_value,
                    "trigger_type": e.trigger_type,
                }
                for e in events
            ],
        )
        APIPLifecycle._persist(record)
        return record

    # ------------------------------------------------------------------
    # Phase 2 — Cause Attribution
    # ------------------------------------------------------------------

    @staticmethod
    def attribute_cause(apip: APIP, agent: "BaseAgent") -> FailureMode:
        snapshots = list(agent._snapshots)
        if not snapshots:
            report = CauseAttributionReport(
                failure_mode=FailureMode.UNKNOWN,
                confidence=0.0,
                reasoning="No snapshot history available.",
            )
            apip.attribution = report
            apip.phase = APIPPhase.ATTRIBUTION
            APIPLifecycle._persist(apip)
            return FailureMode.UNKNOWN

        latest = snapshots[-1].to_metrics()
        history_window = snapshots[-10:]

        citation_rate = latest.get("policy_citation_error_rate", 0)
        hallucination_rate = latest.get("hallucination_rate", 0)
        tool_misuse = latest.get("tool_misuse_rate", 0)
        csat = latest.get("csat_score", 5.0)
        task_rate = latest.get("task_completion_rate", 1.0)

        baseline = agent.contract.metrics
        csat_baseline = baseline.get("csat_score", 4.0)

        # CSAT trend over window
        csat_values = [s.csat_score for s in history_window]
        csat_trend = (csat_values[-1] - csat_values[0]) if len(csat_values) > 1 else 0.0

        # Check trigger events for disaggregation hint
        trigger_metrics = {e["metric_name"] for e in apip.trigger_events}

        if citation_rate > baseline.get("policy_citation_error_rate", 0) * 1.5 \
                and hallucination_rate > baseline.get("hallucination_rate", 0) * 1.5:
            mode = FailureMode.BEHAVIORAL_DRIFT
            confidence = min(0.95, 0.6 + (citation_rate + hallucination_rate) * 2)
            reasoning = (
                f"Both policy_citation_error_rate ({citation_rate:.3f}) and "
                f"hallucination_rate ({hallucination_rate:.3f}) are elevated above "
                f"1.5× baseline, consistent with a stale RAG index."
            )

        elif task_rate >= agent.contract.thresholds.get("task_completion_rate", 0) \
                and "task_completion_rate" not in trigger_metrics \
                and tool_misuse < baseline.get("tool_misuse_rate", 0) * 2:
            # Overall task ok but something else triggered — suggest hidden category failure
            mode = FailureMode.INPUT_BRITTLENESS
            confidence = 0.65
            reasoning = (
                "Overall task_completion_rate appears healthy but other signals suggest "
                "a subcategory may be failing silently. Disaggregated metric review recommended."
            )

        elif csat_trend < -0.2 and csat > agent.contract.thresholds.get("csat_score", 3.8) \
                and tool_misuse < baseline.get("tool_misuse_rate", 0) * 2:
            mode = FailureMode.ALIGNMENT_CREEP
            confidence = min(0.9, 0.55 + abs(csat_trend) * 0.5)
            reasoning = (
                f"CSAT has drifted {csat_trend:.3f} over the last {len(csat_values)} ticks "
                f"while remaining above absolute threshold — classic early-stage alignment creep."
            )

        elif tool_misuse > baseline.get("tool_misuse_rate", 0) * 2 \
                and csat >= agent.contract.thresholds.get("csat_score", 3.8):
            mode = FailureMode.TOOL_MISUSE
            confidence = min(0.95, 0.7 + tool_misuse * 3)
            reasoning = (
                f"tool_misuse_rate spiked to {tool_misuse:.3f} while CSAT ({csat:.2f}) "
                f"remains stable — consistent with a tool schema change causing silent misuse."
            )

        else:
            mode = FailureMode.UNKNOWN
            confidence = 0.3
            reasoning = "No clear pattern matched; manual review required."

        apip.attribution = CauseAttributionReport(
            failure_mode=mode,
            confidence=confidence,
            reasoning=reasoning,
        )
        apip.phase = APIPPhase.ATTRIBUTION
        APIPLifecycle._persist(apip)
        return mode

    # ------------------------------------------------------------------
    # Phase 3 — Intervention Planning
    # ------------------------------------------------------------------

    @staticmethod
    def plan_intervention(failure_mode: FailureMode) -> InterventionPlan:
        plans: dict[FailureMode, tuple[InterventionTier, list[InterventionStep]]] = {
            FailureMode.BEHAVIORAL_DRIFT: (
                InterventionTier.TIER2,
                [
                    InterventionStep(
                        "Re-index the RAG knowledge base with current policy documents.",
                        estimated_effort="medium", expected_impact="high",
                    ),
                    InterventionStep(
                        "Add automated staleness check: alert if index age > 7 days.",
                        estimated_effort="low", expected_impact="medium",
                    ),
                    InterventionStep(
                        "Audit top-20 citation errors and patch prompt grounding instructions.",
                        estimated_effort="low", expected_impact="medium",
                    ),
                ],
            ),
            FailureMode.INPUT_BRITTLENESS: (
                InterventionTier.TIER1,
                [
                    InterventionStep(
                        "Enable disaggregated metric monitoring per input category.",
                        estimated_effort="low", expected_impact="high",
                    ),
                    InterventionStep(
                        "Add targeted few-shot examples for the failing category to the system prompt.",
                        estimated_effort="low", expected_impact="medium",
                    ),
                    InterventionStep(
                        "Collect and label 50+ failure cases from the brittle category for eval.",
                        estimated_effort="medium", expected_impact="high",
                    ),
                ],
            ),
            FailureMode.ALIGNMENT_CREEP: (
                InterventionTier.TIER1,
                [
                    InterventionStep(
                        "Review recent system-prompt changes for tone and brand-voice drift.",
                        estimated_effort="low", expected_impact="medium",
                    ),
                    InterventionStep(
                        "Run CSAT deep-dive: correlate low scores with specific conversation patterns.",
                        estimated_effort="medium", expected_impact="high",
                    ),
                    InterventionStep(
                        "Re-anchor brand voice guidelines in system prompt; add brand-violation eval.",
                        estimated_effort="low", expected_impact="medium",
                    ),
                ],
            ),
            FailureMode.TOOL_MISUSE: (
                InterventionTier.TIER2,
                [
                    InterventionStep(
                        "Audit tool call logs for schema mismatch patterns.",
                        estimated_effort="low", expected_impact="high",
                    ),
                    InterventionStep(
                        "Update tool definitions and re-validate against current schemas.",
                        estimated_effort="medium", expected_impact="high",
                    ),
                    InterventionStep(
                        "Add tool-call validation layer with structured output enforcement.",
                        estimated_effort="medium", expected_impact="medium",
                    ),
                ],
            ),
            FailureMode.UNKNOWN: (
                InterventionTier.TIER3,
                [
                    InterventionStep(
                        "Escalate to AI platform team for manual root-cause analysis.",
                        estimated_effort="high", expected_impact="high",
                    ),
                ],
            ),
        }

        tier, steps = plans[failure_mode]
        return InterventionPlan(tier=tier, steps=steps)

    # ------------------------------------------------------------------
    # Phase 4 — Remediation Window
    # ------------------------------------------------------------------

    @staticmethod
    def open_window(apip: APIP, duration_ticks: int) -> None:
        apip.remediation_window_ticks = duration_ticks
        apip.phase = APIPPhase.REMEDIATION
        APIPLifecycle._persist(apip)

    @staticmethod
    def record_checkin(apip: APIP, snapshot: PerformanceSnapshot) -> CheckIn:
        metrics = snapshot.to_metrics()
        tick = len(apip.checkins) + 1

        trajectory: str
        if len(apip.checkins) < 2:
            trajectory = "flat"
        else:
            prev = apip.checkins[-1].metrics_snapshot
            improvements = 0
            regressions = 0
            for m, v in metrics.items():
                prev_v = prev.get(m, v)
                if m in _HIGHER_IS_WORSE:
                    if v < prev_v:
                        improvements += 1
                    elif v > prev_v:
                        regressions += 1
                else:
                    if v > prev_v:
                        improvements += 1
                    elif v < prev_v:
                        regressions += 1
            if improvements > regressions:
                trajectory = "improving"
            elif regressions > improvements:
                trajectory = "worsening"
            else:
                trajectory = "flat"

        escalated = trajectory == "worsening" and apip.intervention_plan is not None \
            and apip.intervention_plan.tier < InterventionTier.TIER3

        checkin = CheckIn(
            tick=tick,
            metrics_snapshot=metrics,
            trajectory=trajectory,
            escalated=escalated,
        )
        apip.checkins.append(checkin)

        if escalated and apip.intervention_plan:
            apip.intervention_plan = InterventionPlan(
                tier=InterventionTier(min(3, apip.intervention_plan.tier + 1)),
                steps=apip.intervention_plan.steps,
            )

        APIPLifecycle._persist(apip)
        return checkin

    # ------------------------------------------------------------------
    # Phase 5 — Exit Evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_exit(apip: APIP, agent: "BaseAgent") -> ExitOutcome:
        events = agent.evaluate_against_contract()

        if not events:
            outcome: ExitOutcome = "RESOLVED"
        else:
            last_trajectory = apip.checkins[-1].trajectory if apip.checkins else "flat"
            if last_trajectory == "improving":
                outcome = "EXTENDED"
                apip.remediation_window_ticks = int(apip.remediation_window_ticks * 1.5)
            else:
                outcome = "ESCALATED"

        apip.exit_outcome = outcome
        apip.phase = APIPPhase.CLOSED if outcome == "RESOLVED" else APIPPhase.EXIT
        apip.updated_at = datetime.utcnow()
        APIPLifecycle._persist(apip)
        return outcome

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _persist(apip: APIP) -> None:
        apip.updated_at = datetime.utcnow()
        records = _load_apips()
        records[apip.apip_id] = json.loads(
            json.dumps(asdict(apip), default=_serialize)
        )
        _save_apips(records)

    @staticmethod
    def load_all() -> list[dict]:
        return list(_load_apips().values())

    @staticmethod
    def load(apip_id: str) -> dict | None:
        return _load_apips().get(apip_id)
