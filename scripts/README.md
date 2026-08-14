# Scripts

```
scripts/
  lib/latex_build.sh      shared LaTeX build engine — every build.sh wraps this
  papers/<name>/          one directory per paper in papers/
  templates/<conference>/ one directory per conference template in templates/latex/
  web/                    start/stop the product's backend + frontend
  new-paper.sh            scaffold a new paper (papers/ + scripts/papers/ together)
  build_deck.py           regenerate docs/research_paper_workspace.pptx
```

`scripts/papers/` mirrors `papers/`. Adding a paper means adding both, which is
what `new-paper.sh` is for.

## Build a paper

```bash
bash scripts/papers/apip/build.sh          # → papers/apip/latex/main.pdf
```

```bat
scripts\papers\apip\build.bat              :: Windows cmd.exe
```

Runs `pdflatex → bibtex → pdflatex → pdflatex`, then reports the page count plus
any undefined references, undefined citations, or overfull boxes from `main.log`.

| Flag | Effect |
| --- | --- |
| `-c`, `--clean` | Delete `.aux/.bbl/.blg/.log/.out` first — use after editing `references.bib` or renaming a `\label` |
| `-q`, `--quiet` | Hide pdflatex/bibtex chatter; print only the summary |
| `-s DIR`, `--src DIR` | Build a different directory |
| `-h`, `--help` | Usage text |

Every `build.sh` under `papers/` and `templates/` takes these same flags — they
come from `lib/latex_build.sh`, so a fix there reaches all of them at once. The
`.bat` is standalone (batch has no `source`) and must be updated separately.

## Build a conference template

```bash
bash scripts/templates/ieee/build.sh       # → templates/latex/ieee/main.pdf
```

These compile the empty skeletons in `templates/latex/`, which is how you check a
style file still works after updating it. Per-template notes:

- **neurips** — downloads `neurips_<year>.sty` on first build. Bump `STYLE_YEAR`
  and `STYLE_URL` in its `build.sh` annually.
- **aaai** — always cleans aux files first; a stale `main.aux` triggers duplicate
  `\bibstyle` errors under `aaai2026.bst`.
- **acm** / **aaai** — refuse to build if their vendored `.cls`/`.sty` is missing,
  with the download URL in the error.

## Add a paper

```bash
bash scripts/new-paper.sh <slug> [conference]     # conference defaults to ieee
```

Creates `papers/<slug>/{manuscript,latex,figures,deck}/` seeded from
`templates/latex/<conference>/`, plus `scripts/papers/<slug>/build.sh`. Figures
resolve through `\graphicspath` in `main.tex`, so drop images straight into
`papers/<slug>/figures/` and reference them by bare filename.

## TeX Live

Host auto-install is off by default. Set `LATEX_AUTO_INSTALL=1` to let a script
`apt-get` TeX Live, or build with `LATEX_SANDBOX=docker`. On Windows install
[MiKTeX](https://miktex.org) or TeX Live first — the `.bat` has no auto-install
path, since that escape hatch is apt-specific.

# Web Stack Runbook

`scripts/web/` starts and stops the FastAPI backend (`docserver`) and the React
frontend (`web/`).

## Prerequisites

- Python 3.12 with `uv` (preferred), or `python` plus deps from `uv sync`.
- Node.js + npm, already bootstrapped in `web/` (`npm install`).
- Ports `8000` (backend) and `5173` (frontend) free.

## Start and stop

```bash
./scripts/web/start.sh
./scripts/web/stop.sh
```

`start.sh` checks for stale PID files, launches `uvicorn docserver.main:app` on
:8000 with `PYTHONPATH=src`, launches `npm run dev` on :5173, and writes logs and
PIDs under `logs/`. `stop.sh` sends `SIGTERM` to each PID, waits ~5 seconds, then
escalates to `SIGKILL`, cleaning up PID files either way.

## Troubleshooting

- **"Failed to fetch" in the UI:** check the backend started (`tail -f logs/backend.log`).
  Always launch via `start.sh` — it sets the `PYTHONPATH=src` the imports need.
- **Ports already in use:** free 8000/5173, or edit the scripts (keep the
  frontend's `VITE_API_BASE` in sync).
- **Permission denied:** `chmod +x scripts/web/start.sh scripts/web/stop.sh`.
- Use the UI's Delete button or `DELETE /documents/{id}` to remove a workspace.
