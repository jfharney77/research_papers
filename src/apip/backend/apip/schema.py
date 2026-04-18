from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class FailureMode(str, Enum):
    BEHAVIORAL_DRIFT = "behavioral_drift"
    INPUT_BRITTLENESS = "input_brittleness"
    ALIGNMENT_CREEP = "alignment_creep"
    TOOL_MISUSE = "tool_misuse"
    UNKNOWN = "unknown"


class InterventionTier(int, Enum):
    TIER1 = 1   # Prompt / instruction-level fix
    TIER2 = 2   # Retrieval / tool-level fix
    TIER3 = 3   # Retraining / model-level fix


class APIPPhase(str, Enum):
    TRIGGER = "trigger"
    ATTRIBUTION = "attribution"
    INTERVENTION = "intervention"
    REMEDIATION = "remediation"
    EXIT = "exit"
    CLOSED = "closed"


ExitOutcome = Literal["RESOLVED", "EXTENDED", "ESCALATED"]


@dataclass
class CauseAttributionReport:
    failure_mode: FailureMode
    confidence: float           # 0.0 – 1.0
    reasoning: str
    attributed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InterventionStep:
    description: str
    estimated_effort: Literal["low", "medium", "high"]
    expected_impact: Literal["low", "medium", "high"]


@dataclass
class InterventionPlan:
    tier: InterventionTier
    steps: list[InterventionStep]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CheckIn:
    tick: int
    metrics_snapshot: dict[str, float]
    trajectory: Literal["improving", "flat", "worsening"]
    recorded_at: datetime = field(default_factory=datetime.utcnow)
    escalated: bool = False


@dataclass
class APIP:
    apip_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    phase: APIPPhase = APIPPhase.TRIGGER
    trigger_events: list[dict] = field(default_factory=list)
    attribution: CauseAttributionReport | None = None
    intervention_plan: InterventionPlan | None = None
    checkins: list[CheckIn] = field(default_factory=list)
    remediation_window_ticks: int = 0
    exit_outcome: ExitOutcome | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
