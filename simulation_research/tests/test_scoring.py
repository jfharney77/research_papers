import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))
from make_synthetic_panel import make_panel  # noqa: E402

from simsuite.calibsoc import PanelStore, ScoringEngine, StubSimulator
from simsuite.calibsoc.manifest import (
    InstrumentSpec,
    Manifest,
    RunRecord,
    TreatmentSpec,
)


@pytest.fixture(scope="module")
def panel() -> PanelStore:
    return PanelStore(make_panel(n=200, seed=11))


@pytest.fixture(scope="module")
def manifest() -> Manifest:
    return Manifest(
        name="test",
        sample_size=200,
        subgroup_fields=["ideology"],
        instruments=[
            InstrumentSpec(
                name="gov_should_reduce_inequality",
                kind="categorical",
                options=["strongly_agree", "agree", "neutral", "disagree", "strongly_disagree"],
            ),
            InstrumentSpec(name="trust_in_science_0_10", kind="continuous", lo=0, hi=10),
            InstrumentSpec(name="dictator_game_share", kind="continuous", lo=0, hi=1),
        ],
        treatments=[
            TreatmentSpec(
                name="framing_effect",
                instrument="dictator_game_share",
                treatment_field="framing",
                control_value="neutral",
                treatment_value="charity",
                known_effect=0.12,
            )
        ],
    )


def _score(panel: PanelStore, manifest: Manifest, fidelity: float, seed: int = 5):
    truth = {s.name: panel.responses(s.name, wave=1) for s in manifest.instruments}
    sim = StubSimulator(truth, fidelity=fidelity, seed=seed)
    sim.init(panel.personas())
    responses = {s.name: sim.elicit(s) for s in manifest.instruments}
    run = RunRecord(run_id="t", manifest_hash="x", started_at=datetime.now(timezone.utc).isoformat())
    return ScoringEngine(manifest, panel).score(run, responses)


def test_ceilings_are_realistic(panel: PanelStore, manifest: Manifest):
    table = panel.ceiling_table(manifest.instruments)
    assert ((table.ceiling > 0.5) & (table.ceiling <= 1.0)).all()


def test_perfect_simulator_hits_or_exceeds_ceiling(panel: PanelStore, manifest: Manifest):
    report = _score(panel, manifest, fidelity=1.0)
    for s in report.instruments:
        assert s.raw_individual == pytest.approx(1.0)
        assert s.normalized_individual >= 1.0
        assert s.marginal_similarity == pytest.approx(1.0, abs=1e-9)


def test_higher_fidelity_scores_higher(panel: PanelStore, manifest: Manifest):
    good = _score(panel, manifest, fidelity=0.9)
    bad = _score(panel, manifest, fidelity=0.2)
    assert good.mean_normalized_individual > bad.mean_normalized_individual + 0.15


def test_treatment_effect_recovered_by_faithful_sim(panel: PanelStore, manifest: Manifest):
    report = _score(panel, manifest, fidelity=1.0)
    (t,) = report.treatments
    assert t.direction_match
    assert t.magnitude_ratio == pytest.approx(1.0, abs=0.5)


def test_parity_gap_reported(panel: PanelStore, manifest: Manifest):
    report = _score(panel, manifest, fidelity=0.6)
    cat = next(s for s in report.instruments if s.instrument == "gov_should_reduce_inequality")
    assert cat.parity_gap is not None and 0 <= cat.parity_gap <= 1


def test_missing_instrument_skipped(panel: PanelStore, manifest: Manifest):
    run = RunRecord(run_id="t", manifest_hash="x", started_at=datetime.now(timezone.utc).isoformat())
    report = ScoringEngine(manifest, panel).score(run, {})
    assert report.instruments == []
