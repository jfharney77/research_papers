# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status & session summary (2026-08-14)

> Full handoff: see **`AGENTS.md`**. User docs: `docs/guides/MANUAL.md`, `README.md`,
> `docs/guides/DEPLOY-AWS.md`.

Work lives on **`devel-apip-fullfeatures`** and **`devel-reorg`** (neither merged to `main`).
`devel-reorg` restructured the repo into the four content areas described below. The product
(Word → LaTeX workspace) is feature-complete and tested.

Built so far: **dynamic template selection** · **section editing + recompile + build-log** ·
**LaTeX `.zip` export** · **sandboxed LaTeX build + API-key auth + scoped CORS** · **the Critic**
(`src/critic/`: per-section criticisms + AI-genericness score, providers stub/claude/ollama/cerebras) ·
**reference extraction** (`src/docbuilder/refextract.py`) · **AWS deploy** (Dockerfiles + GitHub
Actions ECS Express, verified with Podman; Claude provider baked into the image) · **`MANUAL.md`** ·
a **PowerPoint deck builder** (`scripts/build_deck.py` + `docs/specs/POWERPOINT_SPEC.md`).

Verify with `uv run --group dev pytest` and `npm run build` (in `web/`). Open items and next steps
are listed at the end of `AGENTS.md`.

## Project Skills

- **docx-to-latex** (`.claude/skills/docx-to-latex/SKILL.md`) — convert a `.docx` file into per-section LaTeX files. Trigger: `/docx-to-latex`

When the user types `/docx-to-latex`, invoke the Skill tool with `skill: "docx-to-latex"` before doing anything else.

## What This Repo Does

**The product** is the **Research Paper Workspace**: a Word → LaTeX tool that converts `.docx` manuscripts into per-section LaTeX, builds conference PDFs (IEEE / NeurIPS / ACM / AAAI), and serves a React review UI.

- Product code lives in `src/docbuilder` (converter + CLI), `src/docserver` (FastAPI API), and `web/` (React/Vite).
- **Single entry point:** `python main.py` (backend on :8000), or `scripts/web/start.sh` for backend + frontend.

**Everything else is research content, split by kind.** Four directories, each with its own README:

| Directory | Holds | Rule |
| --- | --- | --- |
| `templates/` | LaTeX + Word styles: `latex/<conference>/` skeletons, `latex/_vendor/` author kits, `bibtex/`, `word/`, `assets/figures/` | Reusable styles only — never real paper content |
| `papers/` | One dir per paper: `manuscript/` · `latex/` · `figures/` · `deck/` | Content only — no styles, no code |
| `sims/` | `apip_sim/` (APIP case-study sim, :8100) · `simsuite/` (CalibSoc + DivProbe) · `figures/` (generators) | All supporting code |
| `docs/` | `specs/` · `guides/` · `research/` (conference deadlines, notes) | Specs and supporting documents |

`scripts/` mirrors this: `scripts/papers/<slug>/` and `scripts/templates/<conference>/` hold thin
wrappers over one shared engine, `scripts/lib/latex_build.sh`. **Add a paper with
`bash scripts/new-paper.sh <slug> [conference]`** — it creates both `papers/<slug>/` and
`scripts/papers/<slug>/build.sh` so the two trees never drift.

## Build Security

The build path compiles LaTeX derived from untrusted uploads, so it runs in a sandbox (`src/docbuilder/sandbox.py`): no shell-escape, restricted TeX file IO, resource limits, and a timeout. Set `LATEX_SANDBOX=docker` for container isolation. The doc server requires an API key when `DOCSERVER_API_KEY` is set (see `src/docserver/auth.py`) and restricts CORS via `DOCSERVER_CORS_ORIGINS`.

## Building LaTeX Papers

Papers and conference templates each get a build script, in two flavors that
mirror each other. **If using WSL (or Linux/macOS), call the `build.sh`
wrappers; if using Windows (cmd.exe / PowerShell), call the `build.bat`
wrappers.** The `.sh` scripts all wrap `scripts/lib/latex_build.sh` and the
`.bat` scripts all wrap `scripts\lib\latex_build.bat`, sharing the same flags
(`-c/--clean`, `-q/--quiet`, `-s/--src`, `-h/--help`), so a fix to an engine
reaches every wrapper on that side:

```bash
# WSL / Linux / macOS
bash scripts/papers/apip/build.sh          # a paper  → papers/apip/latex/main.pdf
bash scripts/papers/apip/run_sim.sh        # its simulation on :8100
```

```bat
:: Windows
scripts\papers\apip\build.bat              :: a paper  → papers\apip\latex\main.pdf
scripts\papers\apip\run_sim.bat            :: its simulation on :8100
```

Conference template skeletons (use these to verify a style file still compiles):

```bash
# WSL — run from repo root; scripts auto-resolve paths
bash scripts/templates/ieee/build.sh
bash scripts/templates/neurips/build.sh
bash scripts/templates/acm/build.sh
bash scripts/templates/aaai/build.sh

# Or with a custom source path
bash scripts/templates/ieee/build.sh /custom/path/to/templates/latex/ieee
```

```bat
:: Windows — same four, same flags
scripts\templates\ieee\build.bat
scripts\templates\neurips\build.bat
scripts\templates\acm\build.bat
scripts\templates\aaai\build.bat
```

All scripts run the standard 4-step pipeline: `pdflatex → bibtex → pdflatex → pdflatex`. The AAAI script also cleans auxiliary files (`.aux`, `.bbl`, `.blg`) before each build.

**Requirements:** `pdflatex`, `bibtex`, TeX Live packages. On WSL, host auto-install is **disabled by default** — set `LATEX_AUTO_INSTALL=1` to allow the scripts to `apt-get install` TeX Live, or build with `LATEX_SANDBOX=docker`. On Windows, install MiKTeX or TeX Live for Windows yourself — the `.bat` scripts have no auto-install path (that escape hatch is apt-specific). When invoked through the doc server, builds always run under the sandbox.

**NeurIPS:** The style file (`neurips_2025.sty`) is auto-downloaded from the NeurIPS website on first build. Update `STYLE_YEAR` and `STYLE_URL` at the top of `scripts/templates/neurips/build.sh` annually.

**ACM:** `acmart.cls` is version-controlled in `templates/latex/acm/`. No download needed.

**AAAI:** `aaai2026.sty` and `aaai2026.bst` are version-controlled in `templates/latex/aaai/`. Update by downloading the author kit from the AAAI website and replacing these files.

## Generating Diagrams

```bash
# Graphviz-based system architecture diagram → ai_architecture.png
python sims/figures/png_gen.py

# Matplotlib transformer/encoder-decoder diagram
# → templates/assets/figures/ai_architecture.{pdf,png}
python sims/figures/generate_diagram.py
```

Templates resolve figures through `\graphicspath` in `main.tex` (the paper's own `figures/`
first, then `templates/assets/figures/`), so reference images by bare filename.

## Python Environment

Uses `uv` for package management. Runtime deps include `fastapi`, `uvicorn`, `python-docx`,
`typer`, and `graphviz` (see `pyproject.toml`); test deps are in the `dev` group.

```bash
uv sync
uv run --group dev pytest        # run the test suite
python main.py                   # run the product backend
uv run python sims/figures/png_gen.py
```

## LaTeX Template Structure

Each template under `templates/latex/<conference>/` follows the same layout:

- `main.tex` — root document; uses `\input{}` to pull in sections
- `sections/` — one file per section (`abstract.tex`, `introduction.tex`, `related_work.tex`, `figures.tex`, `conclusion.tex`)
- `references.bib` — BibTeX bibliography

Edit section files independently; `main.tex` rarely needs changes. This layout is intentional for parallel writing.

## Conference Deadlines

Submission info and deadlines are tracked in `docs/research/conferences2026/`. Key upcoming deadlines:

- **RecSys 2026:** Abstract due 2026-04-14, full paper due 2026-04-21
- **ICDM 2026:** Paper deadline 2026-06-06
- **ICKG 2025:** Submission 2025-07-04
- **IEEE Big Data 2026:** Submission 2026-08-21
