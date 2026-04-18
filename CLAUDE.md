# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Does

A research paper template management system for AI/ML conference submissions. It provides four LaTeX templates (IEEE, NeurIPS, ACM, AAAI), automated build scripts for each, Python diagram generators, and conference deadline tracking for 2026 submissions.

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

**Requirements:** `pdflatex`, `bibtex`, TeX Live packages. Scripts will auto-install via `apt-get` on Linux/WSL if missing.

**NeurIPS:** The style file (`neurips_2025.sty`) is auto-downloaded from the NeurIPS website on first build. Update `STYLE_YEAR` and `STYLE_URL` at the top of `script/latex/neurips/build.sh` annually.

**ACM:** `acmart.cls` is version-controlled in `latex/acm/`. No download needed.

**AAAI:** `aaai2026.sty` and `aaai2026.bst` are version-controlled in `latex/aaai/`. Update by downloading the author kit from the AAAI website and replacing these files.

## Generating Diagrams

```bash
# Graphviz-based system architecture diagram → ai_architecture.png
python src/png_gen.py

# Matplotlib transformer/encoder-decoder diagram → assets/figures/ai_architecture.{pdf,png}
python assets/figures/generate_diagram.py
```

## Python Environment

Uses `uv` for package management. Single runtime dependency: `graphviz>=0.21`.

```bash
uv sync
uv run python src/png_gen.py
```

## LaTeX Template Structure

Each template under `latex/<conference>/` follows the same layout:

- `main.tex` — root document; uses `\input{}` to pull in sections
- `sections/` — one file per section (`abstract.tex`, `introduction.tex`, `related_work.tex`, `figures.tex`, `conclusion.tex`)
- `references.bib` — BibTeX bibliography

Edit section files independently; `main.tex` rarely needs changes. This layout is intentional for parallel writing.

## Conference Deadlines

Submission info and deadlines are tracked in `conferences2026/`. Key upcoming deadlines:

- **RecSys 2026:** Abstract due 2026-04-14, full paper due 2026-04-21
- **ICDM 2026:** Paper deadline 2026-06-06
- **ICKG 2025:** Submission 2025-07-04
- **IEEE Big Data 2026:** Submission 2026-08-21
