"""DivProbe experiment runner: multi-round deliberation with factorial knobs.

Implements the spec's factorial design factors as a config: persona depth,
interaction topology, decoding temperature, and the persona re-injection
intervention. Agents speak through the shared ModelClient (stub by default),
every round is logged to the shared trace schema, and the output feeds
directly into divprobe.metrics.diversity_report.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from simsuite.divprobe.metrics import diversity_report
from simsuite.shared.models import ModelClient
from simsuite.shared.trace import TraceEvent, TraceWriter, context_hash

PERSONA_POOLS = {
    "none": [""],
    "demographic": [
        "a 34-year-old urban renter",
        "a 61-year-old rural homeowner",
        "a 28-year-old graduate student",
        "a 45-year-old small-business owner",
        "a 52-year-old union machinist",
    ],
    "interview": [
        "someone whose spouse's job depends on the affected industry and who distrusts top-down fixes",
        "someone who was laid off in 2020 and now favors strong safety nets over market solutions",
        "someone who runs a food bank and judges every policy by its effect on their clients",
        "someone whose retirement savings track the market and who reads three papers daily",
        "someone who moved countries twice and weighs policies by how they treat outsiders",
    ],
}

TOPOLOGIES = ("fully_connected", "small_world", "islands")


@dataclass
class DeliberationConfig:
    n_agents: int = 12
    n_rounds: int = 10
    question: str = "Should the city adopt congestion pricing downtown?"
    persona_depth: str = "demographic"  # none | demographic | interview
    topology: str = "fully_connected"
    temperature: float = 0.7
    reinject_persona_every: int = 0  # 0 = never (the intervention lever)
    model: str = "stub"
    seed: int = 0
    trace_path: str | Path | None = None


@dataclass
class DeliberationResult:
    rounds_texts: list[list[str]] = field(default_factory=list)
    rounds_stances: list[np.ndarray] = field(default_factory=list)
    shared_contexts: list[str] = field(default_factory=list)

    def metrics(self) -> dict[str, list[float]]:
        return diversity_report(self.rounds_texts, self.rounds_stances, self.shared_contexts)


def _neighbors(topology: str, n: int, rng: random.Random) -> list[list[int]]:
    if topology == "fully_connected":
        return [[j for j in range(n) if j != i] for i in range(n)]
    if topology == "small_world":  # ring + one random long link each
        nb = [[(i - 1) % n, (i + 1) % n, rng.randrange(n)] for i in range(n)]
        return [[j for j in set(js) if j != i] for i, js in enumerate(nb)]
    if topology == "islands":  # 3 cliques, no bridges
        size = max(1, n // 3)
        return [
            [j for j in range(n) if j != i and j // size == i // size]
            for i in range(n)
        ]
    raise ValueError(f"unknown topology {topology!r} (choose from {TOPOLOGIES})")


def _stance_from_text(text: str, rng: random.Random) -> float:
    """Map an utterance to a stance in [-1, 1]; crude lexical scoring + noise."""
    t = text.lower()
    score = 0.0
    for w, v in (("strongly in favor", 1.0), ("favor", 0.5), ("agree", 0.4), ("beneficial", 0.5),
                 ("uncertain", 0.0), ("caution", -0.2), ("disagree", -0.4), ("opposed", -0.8)):
        if w in t:
            score += v
    return float(np.clip(score + rng.gauss(0, 0.1), -1, 1))


def run_deliberation(cfg: DeliberationConfig, client: ModelClient | None = None) -> DeliberationResult:
    client = client or ModelClient()
    rng = random.Random(cfg.seed)
    personas_pool = PERSONA_POOLS[cfg.persona_depth]
    personas = [personas_pool[i % len(personas_pool)] for i in range(cfg.n_agents)]
    neighbors = _neighbors(cfg.topology, cfg.n_agents, rng)

    result = DeliberationResult()
    last_utterances: list[str] = ["" for _ in range(cfg.n_agents)]
    writer = TraceWriter(cfg.trace_path) if cfg.trace_path else None
    episode_id = f"divprobe-{cfg.persona_depth}-{cfg.topology}-seed{cfg.seed}"

    try:
        for rnd in range(cfg.n_rounds):
            reinject = cfg.reinject_persona_every and rnd % cfg.reinject_persona_every == 0
            shared = cfg.question + " Recent remarks: " + " | ".join(
                u for u in last_utterances if u
            )[:800]
            result.shared_contexts.append(shared)
            texts: list[str] = []
            for i in range(cfg.n_agents):
                visible = cfg.question + " " + " | ".join(last_utterances[j] for j in neighbors[i] if last_utterances[j])
                persona_clause = f" You are {personas[i]}." if personas[i] and (rnd == 0 or reinject) else ""
                prompt = f"Round {rnd}.{persona_clause} Debate: {visible[:600]} State your position."
                out = client.complete(prompt, model=cfg.model, temperature=cfg.temperature, seed=cfg.seed * 1000 + i)
                texts.append(out)
                if writer:
                    writer.write(TraceEvent(
                        episode_id=episode_id, agent_id=f"agent{i}", turn=rnd,
                        visible_context_hash=context_hash(visible), action=out,
                        meta={"persona": personas[i], "reinjected": bool(reinject)},
                    ))
            stances = np.array([_stance_from_text(t, rng) for t in texts])
            result.rounds_texts.append(texts)
            result.rounds_stances.append(stances)
            last_utterances = texts
    finally:
        if writer:
            writer.close()
    return result
