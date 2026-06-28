# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status & session summary (2026-06-28)

> Full handoff: see **`AGENTS.md`**. User docs: `MANUAL.md`, `README.md`, `DEPLOY-AWS.md`.

All work lives on branch **`devel-apip-fullfeatures`** (never merged to `main`; has unpushed
commits). The product (Word → LaTeX workspace) is feature-complete and tested; the APIP research
artifacts were moved out to `research/`.

Built so far: **dynamic template selection** · **section editing + recompile + build-log** ·
**LaTeX `.zip` export** · **sandboxed LaTeX build + API-key auth + scoped CORS** · **the Critic**
(`src/critic/`: per-section criticisms + AI-genericness score, providers stub/claude/ollama/cerebras) ·
**reference extraction** (`src/docbuilder/refextract.py`) · **AWS deploy** (Dockerfiles + GitHub
Actions ECS Express, verified with Podman; Claude provider baked into the image) · **`MANUAL.md`** ·
a **PowerPoint deck builder** (`build_deck.py` + `POWERPOINT_SPEC.md`).

Verify with `uv run --group dev pytest` and `npm run build` (in `web/`). Open items and next steps
are listed at the end of `AGENTS.md`.

## Project Skills

- **docx-to-latex** (`.claude/skills/docx-to-latex/SKILL.md`) — convert a `.docx` file into per-section LaTeX files. Trigger: `/docx-to-latex`

When the user types `/docx-to-latex`, invoke the Skill tool with `skill: "docx-to-latex"` before doing anything else.

## What This Repo Does

**The product** is the **Research Paper Workspace**: a Word → LaTeX tool that converts `.docx` manuscripts into per-section LaTeX, builds conference PDFs (IEEE / NeurIPS / ACM / AAAI), and serves a React review UI.

- Product code lives in `src/docbuilder` (converter + CLI), `src/docserver` (FastAPI API), and `web/` (React/Vite).
- **Single entry point:** `python main.py` (backend on :8000), or `scripts/start_web.sh` for backend + frontend.
- LaTeX templates are in `latex/`; per-conference build scripts in `script/latex/`.

**Research artifacts are separate.** The APIP paper (the "New Hire Paradox") and its standalone simulation app live entirely under `research/` and are *not* part of the product:
- `research/apip/` — the paper (docx/pptx/markdown); `research/apip_sim/` — the FastAPI simulation, launched via `research/run_apip.sh` (port 8100).
- `research/conferences2026/` — submission deadlines; `research/assets/`, `research/png_gen.py` — figure generators.

## Build Security

The build path compiles LaTeX derived from untrusted uploads, so it runs in a sandbox (`src/docbuilder/sandbox.py`): no shell-escape, restricted TeX file IO, resource limits, and a timeout. Set `LATEX_SANDBOX=docker` for container isolation. The doc server requires an API key when `DOCSERVER_API_KEY` is set (see `src/docserver/auth.py`) and restricts CORS via `DOCSERVER_CORS_ORIGINS`.

## Building LaTeX Papers

Each conference template has a build script under `script/latex/<conference>/`:

```bash
# Run from repo root — scripts auto-resolve paths
bash script/latex/ieee/build.sh
bash script/latex/neurips/build.sh
bash script/latex/acm/build.sh
bash script/latex/aaai/build.sh

# Or with a custom source path
bash script/latex/ieee/build.sh /custom/path/to/latex/ieee
```

All scripts run the standard 4-step pipeline: `pdflatex → bibtex → pdflatex → pdflatex`. The AAAI script also cleans auxiliary files (`.aux`, `.bbl`, `.blg`) before each build.

**Requirements:** `pdflatex`, `bibtex`, TeX Live packages. Host auto-install is **disabled by default** — set `LATEX_AUTO_INSTALL=1` to allow the scripts to `apt-get install` TeX Live, or build with `LATEX_SANDBOX=docker`. When invoked through the doc server, builds always run under the sandbox.

**NeurIPS:** The style file (`neurips_2025.sty`) is auto-downloaded from the NeurIPS website on first build. Update `STYLE_YEAR` and `STYLE_URL` at the top of `script/latex/neurips/build.sh` annually.

**ACM:** `acmart.cls` is version-controlled in `latex/acm/`. No download needed.

**AAAI:** `aaai2026.sty` and `aaai2026.bst` are version-controlled in `latex/aaai/`. Update by downloading the author kit from the AAAI website and replacing these files.

## Generating Diagrams

```bash
# Graphviz-based system architecture diagram → ai_architecture.png
python research/png_gen.py

# Matplotlib transformer/encoder-decoder diagram → research/assets/figures/ai_architecture.{pdf,png}
python research/assets/figures/generate_diagram.py
```

## Python Environment

Uses `uv` for package management. Runtime deps include `fastapi`, `uvicorn`, `python-docx`,
`typer`, and `graphviz` (see `pyproject.toml`); test deps are in the `dev` group.

```bash
uv sync
uv run --group dev pytest        # run the test suite
python main.py                   # run the product backend
uv run python research/png_gen.py
```

## LaTeX Template Structure

Each template under `latex/<conference>/` follows the same layout:

- `main.tex` — root document; uses `\input{}` to pull in sections
- `sections/` — one file per section (`abstract.tex`, `introduction.tex`, `related_work.tex`, `figures.tex`, `conclusion.tex`)
- `references.bib` — BibTeX bibliography

Edit section files independently; `main.tex` rarely needs changes. This layout is intentional for parallel writing.

## Conference Deadlines

Submission info and deadlines are tracked in `research/conferences2026/`. Key upcoming deadlines:

- **RecSys 2026:** Abstract due 2026-04-14, full paper due 2026-04-21
- **ICDM 2026:** Paper deadline 2026-06-06
- **ICKG 2025:** Submission 2025-07-04
- **IEEE Big Data 2026:** Submission 2026-08-21
