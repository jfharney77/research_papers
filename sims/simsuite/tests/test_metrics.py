import numpy as np
import pytest

from simsuite.divprobe.metrics import (
    TfidfEmbedder,
    diversity_report,
    effective_population_size,
    opinion_drift,
    semantic_dispersion,
    structural_coupling_index,
)

DIVERSE = [
    "Congestion pricing will crush small downtown retailers and commuters.",
    "The climate benefits of fewer cars dwarf every other consideration here.",
    "Transit riders finally get faster buses; equity demands we try it.",
    "I want to see the elasticity estimates before endorsing anything.",
]
COLLAPSED = ["We all agree the policy is beneficial on balance."] * 4


def _embed(texts):
    return TfidfEmbedder().fit(DIVERSE + COLLAPSED).embed(texts)


def test_dispersion_orders_diverse_above_collapsed():
    assert semantic_dispersion(_embed(DIVERSE)) > semantic_dispersion(_embed(COLLAPSED)) + 0.3


def test_identical_outputs_have_zero_dispersion():
    assert semantic_dispersion(_embed(COLLAPSED)) == pytest.approx(0.0, abs=1e-9)


def test_effective_population_size_bounds():
    assert effective_population_size(_embed(COLLAPSED)) == pytest.approx(1.0, abs=1e-6)
    assert effective_population_size(_embed(DIVERSE)) > 2.5


def test_opinion_drift_zero_for_same_distribution():
    stances = np.array([-1.0, -0.3, 0.4, 0.9])
    assert opinion_drift(stances, stances) == 0.0
    assert opinion_drift(stances, np.zeros(4)) > 0.3


def test_structural_coupling_detects_shared_context():
    ctx_text = "the mayors congestion report says pricing is beneficial"
    # Each agent echoes the shared context plus one idiosyncratic point.
    coupled_texts = [f"{ctx_text} but my concern is {w}" for w in ("parking", "buses", "shops", "taxes")]
    corpus = DIVERSE + coupled_texts + [ctx_text]
    emb = TfidfEmbedder().fit(corpus)
    ctx = emb.embed([ctx_text])[0]
    coupled = structural_coupling_index(emb.embed(coupled_texts), ctx)
    uncoupled = structural_coupling_index(emb.embed(DIVERSE), ctx)
    assert coupled > uncoupled + 0.1


def test_diversity_report_shapes():
    rounds = [DIVERSE, COLLAPSED]
    stances = [np.array([-1, -0.5, 0.5, 1.0]), np.zeros(4)]
    contexts = ["round zero context", "round one context"]
    rep = diversity_report(rounds, stances, contexts)
    assert set(rep) == {
        "semantic_dispersion",
        "effective_population_size",
        "opinion_drift",
        "structural_coupling_index",
    }
    assert all(len(v) == 2 for v in rep.values())
    assert rep["semantic_dispersion"][0] > rep["semantic_dispersion"][1]
