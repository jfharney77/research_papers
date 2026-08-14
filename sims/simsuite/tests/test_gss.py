"""Tests against the real GSS panel file; skipped unless it has been downloaded
(run examples/calibsoc_gss_demo.py once, or download_gss_panel())."""

from pathlib import Path

import pytest

DTA = Path(__file__).parent.parent / "data" / "raw" / "gss2020panel_r1a.dta"

pytestmark = pytest.mark.skipif(not DTA.exists(), reason="GSS panel file not downloaded")


@pytest.fixture(scope="module")
def gss():
    from simsuite.calibsoc.gss import load_gss_panel

    return load_gss_panel(DTA)


def test_panel_shape(gss):
    panel, specs = gss
    personas = panel.personas()
    assert len(personas) > 1500  # ~1.8k respondents with both-wave responses
    assert {"sex", "race", "degree", "partyid", "age"} <= set(personas.columns)
    assert len(specs) == 8


def test_every_instrument_has_both_waves(gss):
    panel, specs = gss
    for spec in specs:
        w1 = panel.responses(spec.name, wave=1)
        w2 = panel.responses(spec.name, wave=2)
        assert len(w1.index.intersection(w2.index)) > 500, spec.name


def test_ceilings_in_plausible_stability_range(gss):
    panel, specs = gss
    table = panel.ceiling_table(specs)
    # 2-4 year attitude stability: well above chance, below 2-week test-retest.
    assert (table.ceiling > 0.45).all(), table
    assert (table.ceiling < 1.0).all(), table


def test_categorical_responses_are_labels_not_codes(gss):
    panel, _ = gss
    vals = set(panel.responses("cappun", wave=1).unique())
    assert vals <= {"favor", "oppose"}
