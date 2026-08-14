"""SimulatorAdapter interface + reference adapters.

Spec: `init(personas) -> AgentPool`, `run(scenario) -> Transcript`,
`elicit(instrument) -> Responses`, so any simulator plugs in with ~200 LOC.

Two reference adapters ship here:
- StubSimulator: persona-driven statistical responder (no LLM). Deterministic
  under a seed; its accuracy is tunable, which makes it the test fixture for
  the scoring engine ("a simulator with known fidelity X must score ~X").
- LLMLoopSimulator: the "plain API loop" adapter from the spec — one
  prompt-per-persona elicitation through the shared ModelClient. With the
  StubProvider it runs free; point ModelClient at litellm for real models.

Concordia/OASIS adapters are future work and belong in their own modules.
"""

from __future__ import annotations

import random
from typing import Protocol

import pandas as pd

from simsuite.calibsoc.manifest import InstrumentSpec
from simsuite.shared.models import ModelClient


class SimulatorAdapter(Protocol):
    def init(self, personas: pd.DataFrame) -> None: ...
    def run(self, scenario: str) -> list[str]: ...
    def elicit(self, instrument: InstrumentSpec) -> pd.Series: ...


class StubSimulator:
    """Statistical responder with controllable fidelity.

    With probability `fidelity` an agent reproduces its person's true wave-1
    answer (supplied via ground_truth); otherwise it answers from a
    persona-biased distribution. fidelity=1.0 -> perfect simulator,
    fidelity=0.0 -> persona-only baseline.
    """

    def __init__(self, ground_truth: dict[str, pd.Series], fidelity: float = 0.7, seed: int = 0):
        self.ground_truth = ground_truth  # instrument name -> person_id-indexed answers
        self.fidelity = fidelity
        self.seed = seed
        self.personas: pd.DataFrame | None = None

    def init(self, personas: pd.DataFrame) -> None:
        self.personas = personas.reset_index(drop=True)

    def run(self, scenario: str) -> list[str]:
        return [f"[stub transcript for scenario: {scenario}]"]

    def elicit(self, instrument: InstrumentSpec) -> pd.Series:
        assert self.personas is not None, "call init() first"
        truth = self.ground_truth[instrument.name]
        rng = random.Random(f"{self.seed}|{instrument.name}")
        out: dict[str, object] = {}
        for _, p in self.personas.iterrows():
            pid = p["person_id"]
            if pid in truth.index and rng.random() < self.fidelity:
                out[pid] = truth.loc[pid]
            else:
                out[pid] = self._persona_answer(p, instrument, rng)
        return pd.Series(out, name=instrument.name)

    def _persona_answer(self, p: pd.Series, spec: InstrumentSpec, rng: random.Random) -> object:
        if spec.kind == "categorical":
            # Bias by an ideology-like column when present, else uniform.
            opts = spec.options or ["agree", "disagree"]
            if "ideology" in p.index and len(opts) >= 2:
                lean = 0 if str(p["ideology"]).startswith(("lib", "left")) else len(opts) - 1
                return opts[lean] if rng.random() < 0.6 else rng.choice(opts)
            return rng.choice(opts)
        lo, hi = spec.lo or 0.0, spec.hi or 1.0
        return round(rng.uniform(lo, hi), 3)


class LLMLoopSimulator:
    """One elicitation prompt per persona through the shared ModelClient."""

    def __init__(self, client: ModelClient, model: str = "stub", temperature: float = 0.7):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.personas: pd.DataFrame | None = None

    def init(self, personas: pd.DataFrame) -> None:
        self.personas = personas.reset_index(drop=True)

    def run(self, scenario: str) -> list[str]:
        return []  # this adapter elicits directly; no group scenario phase

    def elicit(self, instrument: InstrumentSpec) -> pd.Series:
        assert self.personas is not None, "call init() first"
        out: dict[str, object] = {}
        for i, p in self.personas.iterrows():
            persona_desc = ", ".join(f"{k}={p[k]}" for k in p.index if k != "person_id")
            if instrument.kind == "categorical":
                prompt = (
                    f"You are simulating a survey respondent ({persona_desc}). "
                    f"Question: {instrument.name}. "
                    f"Answer with exactly one of: {', '.join(instrument.options)}."
                )
            else:
                prompt = (
                    f"You are simulating a survey respondent ({persona_desc}). "
                    f"Question: {instrument.name}. "
                    f"Answer with a number between {instrument.lo} and {instrument.hi}."
                )
            raw = self.client.complete(prompt, model=self.model, temperature=self.temperature, seed=i)
            out[p["person_id"]] = _parse_response(raw, instrument)
        return pd.Series(out, name=instrument.name)


def _parse_response(raw: str, spec: InstrumentSpec) -> object:
    text = raw.strip().lower()
    if spec.kind == "categorical":
        for opt in spec.options:
            if opt.lower() in text:
                return opt
        return spec.options[0] if spec.options else text
    for token in text.replace(",", " ").split():
        try:
            val = float(token)
        except ValueError:
            continue
        lo, hi = spec.lo or float("-inf"), spec.hi or float("inf")
        return min(max(val, lo), hi)
    return ((spec.lo or 0.0) + (spec.hi or 1.0)) / 2
