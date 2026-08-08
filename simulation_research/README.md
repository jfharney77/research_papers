# simulation_research

Working directory for finding a research niche in **multi-agent simulation** (classical ABM × LLM agents).

## Contents

| File / dir | What it is |
|---|---|
| `compass_artifact_…_text_markdown.md` | Deep-research review: 10 papers + 10 platforms, 7 cross-cutting open problems, 8 novel paper ideas |
| `implementation_specs.md` | Engineering specs for the 8 proposed projects (4 full, 4 condensed) |
| `simsuite/` | Working implementation of the first two projects, per the specs' build order **1 → 4 → 2** |
| `examples/` | End-to-end demos (run offline on a deterministic stub provider — zero API spend) |
| `tests/` | pytest suite (22 tests) |
| `data/` | Synthetic panel + JSONL traces (generated; safe to delete) |

## The niche thesis

Every primary source in the review concedes the same thing: LLM social simulations are
**believable but not validated**. The thinnest-covered, highest-impact gaps are (a) calibration
against real human panel data and (b) diversity collapse in agent populations — both cheap to
prototype and both prerequisites for anything at scale. That is where `simsuite` starts:

- **`simsuite/calibsoc/`** — Project 1 (*CalibSoc*): pre-registered calibration harness.
  Frozen-manifest pre-registration (`manifest.py` — scoring refuses runs whose manifest was
  edited after freezing or that started before the freeze), a `SimulatorAdapter` protocol with
  two reference adapters (`adapters.py`), a two-wave panel store that computes human
  test-retest ceilings (`panel.py`), and a scoring engine (`scoring.py`) reporting
  **normalized accuracy** (sim-vs-human / human-vs-human-retest) at three levels: individual,
  marginal distribution (Wasserstein), and treatment-effect recovery — plus the
  demographic-parity gap from Park et al. 2024.
- **`simsuite/divprobe/`** — Project 4 (*DivProbe*): diversity-collapse diagnostics.
  Four trajectory metrics (`metrics.py`): semantic dispersion, opinion-distribution drift,
  effective population size (exp-entropy of cluster occupancy), and a structural coupling
  index separating "agents converged" from "agents read the same thing". Plus a factorial
  deliberation runner (`experiment.py`) with topology / persona-depth / temperature /
  persona-re-injection knobs.
- **`simsuite/shared/`** — the specs' shared infrastructure: one JSONL trace schema
  (`trace.py`) all projects read/write, and a cached model-access layer (`models.py`) with a
  deterministic stub provider (default) or `litellm` passthrough for real models.

## Quickstart

```bash
cd simulation_research
uv sync --group dev
uv run --group dev pytest                 # 22 tests
uv run python examples/make_synthetic_panel.py
uv run python examples/calibsoc_demo.py       # synthetic panel: freeze manifest → simulate → score
uv run python examples/calibsoc_gss_demo.py   # REAL DATA: GSS 2016-2020 panel (auto-downloads ~12MB)
uv run python examples/divprobe_demo.py       # collapse baseline vs re-injection intervention
```

### Real data: GSS 2016–2020 panel

`simsuite/calibsoc/gss.py` ingests NORC's public GSS panel release (2016/2018 respondents
re-interviewed in 2020; no registration needed) into the PanelStore format: 1,823 respondents
with both-wave responses on an 8-instrument battery (polviews, eqwlth, attend, natfare, trust,
happy, cappun, grass) plus demographic personas (age, sex, race, degree, partyid). Measured
human stability ceilings range from **0.52 (happy)** to **0.87 (polviews)** — real numbers that
replace the synthetic ones as normalization denominators. Caveat: the 2–4-year wave gap
measures attitude *stability*, not the 2-week test-retest reliability Park et al. 2024 used, so
these ceilings are lower and normalized accuracy is correspondingly generous. ANES panel data
would sharpen this but requires registered download; the ingest module is the template.

The CalibSoc demo reproduces, in miniature, the headline pattern of Park et al. 2024: a
rich-persona simulator clears the human test-retest ceiling (normalized ≈ 1.04) while a
demographics-only simulator lands at ≈ 0.77 with a 3× larger demographic-parity gap and only
half the true treatment effect. The DivProbe demo shows a low-temperature population collapsing
to ~2 effective voices with high structural coupling, and interview-persona re-injection holding
~5–7 voices.

## Next steps (in spec order)

1. ~~**Real data**~~: done — GSS 2016–2020 panel wired in (`simsuite/calibsoc/gss.py`). ANES
   re-interviews (registered download) remain the path to a true short-gap ceiling.
2. **Real models**: `pip install litellm`, pass `LiteLLMProvider()` to `ModelClient`, and rerun
   the demo grid — this is the Weeks 4–6 baseline experiment from the Project 1 spec.
3. **Project 2 (AsymBench)**: the belief-probe/information-ledger design plugs into the same
   trace schema (`probes` field is already there).
4. Reference adapters for Concordia and OASIS (~200 LOC each against `SimulatorAdapter`).
