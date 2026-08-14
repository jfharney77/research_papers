# Simulations and supporting code

Code that backs the papers. Each simulation is independent; nothing here is part
of the Word→LaTeX product in `src/`.

| Directory | What it is |
| --- | --- |
| `apip_sim/` | FastAPI simulation behind the APIP paper's case study — agent mesh, degradation scenarios, APIP lifecycle. Start with `bash scripts/papers/apip/run_sim.sh` (port 8100). |
| `simsuite/` | Multi-agent simulation research suite: CalibSoc (calibration against real GSS panel data) and DivProbe (diversity collapse). Has its own `pyproject.toml` and test suite. |
| `figures/` | Figure generators — `generate_diagram.py` (matplotlib, writes into `templates/assets/figures/`) and `png_gen.py` (graphviz architecture diagram). |

`simsuite/` is a self-contained project:

```bash
cd sims/simsuite && uv sync && uv run pytest
```

Its research background is in `docs/research/compass_artifact_diversity_metrics.md`
and its engineering specs in `docs/specs/simsuite_implementation_specs.md`.
