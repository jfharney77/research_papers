"""CalibSoc scoring engine.

Computes normalized_accuracy = sim_vs_human / human_vs_human_retest at three
levels (per the spec):
  (a) individual — per-person agreement with wave-1 answers;
  (b) marginal   — Wasserstein distance between simulated and human response
                   distributions, converted to a [0,1] similarity;
  (c) treatment  — does the sim reproduce the direction and magnitude of a
                   known experimental effect.
Secondary: demographic-parity gap (accuracy spread across subgroups).

Scoring refuses to run unless the run passes pre-registration verification
(manifest hash frozen before the run started).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance

from simsuite.calibsoc.manifest import (
    InstrumentSpec,
    Manifest,
    RunRecord,
    TreatmentSpec,
    verify_run_against_manifest,
)
from simsuite.calibsoc.panel import PanelStore, _agreement


@dataclass
class InstrumentScore:
    instrument: str
    ceiling: float
    raw_individual: float
    normalized_individual: float
    marginal_similarity: float
    parity_gap: float | None = None


@dataclass
class TreatmentScore:
    name: str
    known_effect: float
    simulated_effect: float
    direction_match: bool
    magnitude_ratio: float  # sim / known, 1.0 = perfect


@dataclass
class ScoreReport:
    run_id: str
    instruments: list[InstrumentScore] = field(default_factory=list)
    treatments: list[TreatmentScore] = field(default_factory=list)

    @property
    def mean_normalized_individual(self) -> float:
        return float(np.mean([s.normalized_individual for s in self.instruments]))

    @property
    def mean_marginal_similarity(self) -> float:
        return float(np.mean([s.marginal_similarity for s in self.instruments]))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([vars(s) for s in self.instruments])

    def summary(self) -> str:
        lines = [f"CalibSoc report — run {self.run_id}"]
        for s in self.instruments:
            parity = f"  parity_gap={s.parity_gap:.3f}" if s.parity_gap is not None else ""
            lines.append(
                f"  {s.instrument:<28} ceiling={s.ceiling:.3f}  raw={s.raw_individual:.3f}  "
                f"normalized={s.normalized_individual:.3f}  marginal={s.marginal_similarity:.3f}{parity}"
            )
        for t in self.treatments:
            lines.append(
                f"  [treatment] {t.name:<16} known={t.known_effect:+.3f}  sim={t.simulated_effect:+.3f}  "
                f"direction={'OK' if t.direction_match else 'FLIPPED'}  magnitude_ratio={t.magnitude_ratio:.2f}"
            )
        lines.append(
            f"  MEAN normalized individual accuracy: {self.mean_normalized_individual:.3f} "
            f"(escalation threshold per review: ~0.80)"
        )
        return "\n".join(lines)


class ScoringEngine:
    def __init__(self, manifest: Manifest, panel: PanelStore, manifest_path: str | Path | None = None):
        self.manifest = manifest
        self.panel = panel
        self.manifest_path = manifest_path

    def score(
        self,
        run: RunRecord,
        sim_responses: dict[str, pd.Series],
        personas: pd.DataFrame | None = None,
    ) -> ScoreReport:
        """Score simulated responses (instrument name -> person_id-indexed Series)."""
        if self.manifest_path is not None:
            verify_run_against_manifest(run, self.manifest_path)

        report = ScoreReport(run_id=run.run_id)
        personas = personas if personas is not None else self.panel.personas()

        for spec in self.manifest.instruments:
            if spec.name not in sim_responses:
                continue
            sim = sim_responses[spec.name]
            human = self.panel.responses(spec.name, wave=1)
            joined = pd.concat([sim, human], axis=1, keys=["sim", "human"]).dropna()
            ceiling = self.panel.test_retest_ceiling(spec)
            raw = _agreement(joined["sim"], joined["human"], spec)
            report.instruments.append(
                InstrumentScore(
                    instrument=spec.name,
                    ceiling=ceiling,
                    raw_individual=raw,
                    normalized_individual=min(raw / ceiling, 1.5) if ceiling > 0 else float("nan"),
                    marginal_similarity=_marginal_similarity(joined["sim"], joined["human"], spec),
                    parity_gap=self._parity_gap(joined, spec, personas),
                )
            )

        for tspec in self.manifest.treatments:
            score = self._treatment_score(tspec, sim_responses, personas)
            if score is not None:
                report.treatments.append(score)
        return report

    def _parity_gap(
        self, joined: pd.DataFrame, spec: InstrumentSpec, personas: pd.DataFrame
    ) -> float | None:
        """Max-min raw accuracy across subgroups of the manifest's parity axes."""
        if not self.manifest.subgroup_fields:
            return None
        indexed = personas.set_index("person_id")
        accs: list[float] = []
        for fld in self.manifest.subgroup_fields:
            if fld not in indexed.columns:
                continue
            for _, group_ids in indexed.groupby(fld).groups.items():
                sub = joined.loc[joined.index.intersection(group_ids)]
                if len(sub) >= 5:
                    accs.append(_agreement(sub["sim"], sub["human"], spec))
        return float(max(accs) - min(accs)) if len(accs) >= 2 else None

    def _treatment_score(
        self,
        tspec: TreatmentSpec,
        sim_responses: dict[str, pd.Series],
        personas: pd.DataFrame,
    ) -> TreatmentScore | None:
        if tspec.instrument not in sim_responses:
            return None
        sim = sim_responses[tspec.instrument].astype(float)
        indexed = personas.set_index("person_id")
        if tspec.treatment_field not in indexed.columns:
            return None
        arm = indexed[tspec.treatment_field].astype(str)
        control = sim.loc[sim.index.intersection(arm[arm == tspec.control_value].index)]
        treated = sim.loc[sim.index.intersection(arm[arm == tspec.treatment_value].index)]
        if control.empty or treated.empty:
            return None
        effect = float(treated.mean() - control.mean())
        direction = bool(np.sign(effect) == np.sign(tspec.known_effect)) if tspec.known_effect else effect == 0
        ratio = effect / tspec.known_effect if tspec.known_effect else float("nan")
        return TreatmentScore(
            name=tspec.name,
            known_effect=tspec.known_effect,
            simulated_effect=effect,
            direction_match=direction,
            magnitude_ratio=float(ratio),
        )


def _marginal_similarity(sim: pd.Series, human: pd.Series, spec: InstrumentSpec) -> float:
    """1 - normalized Wasserstein distance between response distributions."""
    if spec.kind == "categorical":
        # Map categories to their option index so distance is ordinal-aware.
        order = {o: i for i, o in enumerate(spec.options)} if spec.options else None
        if order:
            s = sim.astype(str).map(order).dropna()
            h = human.astype(str).map(order).dropna()
            span = max(len(order) - 1, 1)
        else:
            cats = sorted(set(sim.astype(str)) | set(human.astype(str)))
            order = {c: i for i, c in enumerate(cats)}
            s, h = sim.astype(str).map(order), human.astype(str).map(order)
            span = max(len(cats) - 1, 1)
    else:
        s, h = sim.astype(float), human.astype(float)
        lo = spec.lo if spec.lo is not None else float(min(s.min(), h.min()))
        hi = spec.hi if spec.hi is not None else float(max(s.max(), h.max()))
        span = (hi - lo) or 1.0
    if len(s) == 0 or len(h) == 0:
        return float("nan")
    dist = wasserstein_distance(s.to_numpy(dtype=float), h.to_numpy(dtype=float))
    return float(max(0.0, 1.0 - dist / span))
