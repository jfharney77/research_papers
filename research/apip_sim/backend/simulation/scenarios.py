from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .degradation import DegradationEngine, DegradationMode

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent, PerformanceSnapshot


@dataclass
class ScenarioStep:
    tick: int
    mode: DegradationMode
    intensity: float


@dataclass
class Scenario:
    name: str
    description: str
    steps: list[ScenarioStep]

    def apply_at_tick(self, engine: DegradationEngine, tick: int) -> None:
        for step in self.steps:
            if step.tick == tick:
                engine.inject(step.mode, step.intensity)

    def reset(self, engine: DegradationEngine) -> None:
        engine.reset()


def run_scenario(
    scenario: Scenario,
    agent: "BaseAgent",
    total_ticks: int = 20,
) -> list["PerformanceSnapshot"]:
    engine = DegradationEngine(agent)
    snapshots: list["PerformanceSnapshot"] = []

    for tick in range(1, total_ticks + 1):
        scenario.apply_at_tick(engine, tick)
        snapshot = engine.tick()
        snapshots.append(snapshot)

    return snapshots


# ---------------------------------------------------------------------------
# Named scenarios
# ---------------------------------------------------------------------------

STALE_RAG_DRIFT = Scenario(
    name="stale_rag_drift",
    description=(
        "Simulates a stale RAG index causing gradually increasing citation errors "
        "and hallucinations. Slow onset that accelerates after tick 5."
    ),
    steps=[
        ScenarioStep(tick=1, mode=DegradationMode.BEHAVIORAL_DRIFT, intensity=0.4),
    ],
)

BILLING_BRITTLENESS = Scenario(
    name="billing_brittleness",
    description=(
        "A specific input category (billing_dispute) starts failing while overall "
        "task completion appears healthy. Hidden without disaggregated monitoring."
    ),
    steps=[
        ScenarioStep(tick=1, mode=DegradationMode.INPUT_BRITTLENESS, intensity=0.6),
    ],
)

SLOW_BRAND_EROSION = Scenario(
    name="slow_brand_erosion",
    description=(
        "Alignment creep: CSAT drifts slowly downward and brand violation flags "
        "accumulate. Stays within absolute thresholds until late stage, only "
        "detectable via drift monitoring."
    ),
    steps=[
        ScenarioStep(tick=1, mode=DegradationMode.ALIGNMENT_CREEP, intensity=0.5),
    ],
)

TOOL_SCHEMA_BREAK = Scenario(
    name="tool_schema_break",
    description=(
        "A tool schema change causes sudden tool_misuse spikes. CSAT and "
        "task_completion remain unaffected initially, making this hard to detect "
        "without dedicated tool-log monitoring."
    ),
    steps=[
        ScenarioStep(tick=3, mode=DegradationMode.TOOL_MISUSE, intensity=0.8),
    ],
)

COMPOUNDING_FAILURE = Scenario(
    name="compounding_failure",
    description=(
        "Behavioral drift begins at tick 1, then a tool schema break hits at "
        "tick 6, compounding into a multi-vector degradation that strains "
        "single-metric alerting."
    ),
    steps=[
        ScenarioStep(tick=1, mode=DegradationMode.BEHAVIORAL_DRIFT, intensity=0.3),
        ScenarioStep(tick=6, mode=DegradationMode.TOOL_MISUSE, intensity=0.7),
    ],
)

ALL_SCENARIOS: dict[str, Scenario] = {
    s.name: s
    for s in [
        STALE_RAG_DRIFT,
        BILLING_BRITTLENESS,
        SLOW_BRAND_EROSION,
        TOOL_SCHEMA_BREAK,
        COMPOUNDING_FAILURE,
    ]
}
