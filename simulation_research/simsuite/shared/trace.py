"""Shared JSONL episode trace schema.

The specs' "Shared Infrastructure Notes" call for one JSONL episode schema
(agent_id, tier, turn, visible_context_hash, action, probes) used across all
projects so CalibSoc/DivProbe can score runs produced by any other project.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, Field


def context_hash(visible_context: str) -> str:
    """Stable hash of the context a decision was made against."""
    return hashlib.sha256(visible_context.encode("utf-8")).hexdigest()[:16]


class TraceEvent(BaseModel):
    """One agent decision (or probe response) inside an episode."""

    episode_id: str
    agent_id: str
    turn: int
    tier: int = 0  # 0 = full LLM, 1 = distilled, 2 = rule-based (TieredSim convention)
    visible_context_hash: str = ""
    action: str = ""
    probes: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class TraceWriter:
    """Append-only JSONL writer for TraceEvents."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def write(self, event: TraceEvent) -> None:
        self._fh.write(json.dumps(event.model_dump(), ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_trace(path: str | Path) -> Iterator[TraceEvent]:
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield TraceEvent.model_validate_json(line)
