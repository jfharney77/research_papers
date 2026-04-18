from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, stdev
from typing import Literal


@dataclass
class BehavioralContract:
    task_surface: list[str]
    metrics: dict[str, float]          # metric name -> baseline value at deployment
    thresholds: dict[str, float]       # metric name -> minimum acceptable value
    drift_sensitivity: float           # std deviations that trigger a drift alert
    owner: str
    created_at: datetime


@dataclass
class PerformanceSnapshot:
    timestamp: datetime
    task_completion_rate: float
    csat_score: float
    policy_citation_error_rate: float
    tool_misuse_rate: float
    hallucination_rate: float
    notes: str = ""

    def to_metrics(self) -> dict[str, float]:
        return {
            "task_completion_rate": self.task_completion_rate,
            "csat_score": self.csat_score,
            "policy_citation_error_rate": self.policy_citation_error_rate,
            "tool_misuse_rate": self.tool_misuse_rate,
            "hallucination_rate": self.hallucination_rate,
        }


@dataclass
class TriggerEvent:
    metric_name: str
    observed_value: float
    threshold_value: float
    trigger_type: Literal["absolute", "drift"]


# Metrics where higher is worse (breach = observed > threshold)
_HIGHER_IS_WORSE = {
    "policy_citation_error_rate",
    "tool_misuse_rate",
    "hallucination_rate",
}


class BaseAgent:
    def __init__(self, agent_id: str, agent_name: str, role: str,
                 contract: BehavioralContract) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.role = role
        self.contract = contract
        self._snapshots: deque[PerformanceSnapshot] = deque(maxlen=30)

    def record_snapshot(self, snapshot: PerformanceSnapshot) -> None:
        self._snapshots.append(snapshot)

    def latest_snapshot(self) -> PerformanceSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def evaluate_against_contract(self) -> list[TriggerEvent]:
        snapshot = self.latest_snapshot()
        if snapshot is None:
            return []

        current = snapshot.to_metrics()
        events: list[TriggerEvent] = []

        for metric, threshold in self.contract.thresholds.items():
            observed = current.get(metric)
            if observed is None:
                continue

            # Absolute threshold check
            breached = (
                observed > threshold if metric in _HIGHER_IS_WORSE
                else observed < threshold
            )
            if breached:
                events.append(TriggerEvent(
                    metric_name=metric,
                    observed_value=observed,
                    threshold_value=threshold,
                    trigger_type="absolute",
                ))
                continue  # absolute breach already flagged; skip drift check

            # Drift check against rolling window
            history = [s.to_metrics()[metric] for s in self._snapshots
                       if metric in s.to_metrics()]
            if len(history) >= 5:
                mu = mean(history)
                sigma = stdev(history)
                if sigma > 0:
                    z = (observed - mu) / sigma
                    # For higher-is-worse metrics, positive z is the bad direction
                    drift_z = z if metric in _HIGHER_IS_WORSE else -z
                    if drift_z > self.contract.drift_sensitivity:
                        events.append(TriggerEvent(
                            metric_name=metric,
                            observed_value=observed,
                            threshold_value=threshold,
                            trigger_type="drift",
                        ))

        return events

    def get_health_status(self) -> Literal["healthy", "degraded", "critical"]:
        events = self.evaluate_against_contract()
        absolute_breaches = sum(1 for e in events if e.trigger_type == "absolute")
        if absolute_breaches >= 2:
            return "critical"
        if absolute_breaches == 1 or events:
            return "degraded"
        return "healthy"
