# Research Paper Workspace

A **Word → LaTeX tool**: upload a `.docx` manuscript, convert it into per-section LaTeX,
build a conference-ready PDF (IEEE / NeurIPS / ACM / AAAI), and review/edit it in a web UI.

## Run it

```bash
python main.py            # product backend (FastAPI) on http://localhost:8000
scripts/web/start.sh      # backend + React dev server (http://localhost:5173)
papers convert paper.docx --template ieee   # CLI conversion
```

**Layout:** the product is `src/docbuilder` (converter + CLI), `src/docserver` (API), and
`web/` (React). Research content is split into `templates/` (styles), `papers/` (content),
`sims/` (supporting code) and `docs/` (specs) — see [Repository Structure](#repository-structure).

**Security:** the LaTeX build runs sandboxed (no shell-escape, restricted file IO,
resource limits, timeout — see `src/docbuilder/sandbox.py`; `LATEX_SANDBOX=docker` for
container isolation). Set `DOCSERVER_API_KEY` to require auth, and `DOCSERVER_CORS_ORIGINS`
to allowlist browser origins.

---

## Repository Structure

Four content areas, plus the product. Each has its own README.

```
research_papers/
├── templates/                  # (1) styles — reusable, never paper content
│   ├── latex/
│   │   ├── ieee/               #     conference skeletons: main.tex + sections/
│   │   ├── neurips/            #     neurips_YYYY.sty auto-downloaded on first build
│   │   ├── acm/                #     acmart.cls version-controlled
│   │   ├── aaai/               #     aaaiYY.sty + .bst version-controlled
│   │   └── _vendor/            #     upstream author kits, kept verbatim
│   ├── bibtex/                 #     shared IEEEtran .bst + IEEE .bib abbreviations
│   ├── word/                   #     Word style templates (.dotx, reference.docx)
│   └── assets/figures/         #     placeholder figures the skeletons reference
│
├── papers/                     # (2) content — one directory per paper
│   └── apip/
│       ├── manuscript/         #     .docx / .md sources
│       ├── latex/              #     main.tex + sections/ — the build target
│       ├── figures/
│       └── deck/
│
├── sims/                       # (3) simulations and supporting code
│   ├── apip_sim/               #     APIP case-study simulation (:8100)
│   ├── simsuite/               #     CalibSoc + DivProbe research suite
│   └── figures/                #     figure generators
│
├── docs/                       # (4) specs and supporting documents
│   ├── specs/                  #     feature/design specs
│   ├── guides/                 #     MANUAL.md, DEPLOY-AWS.md, ...
│   └── research/               #     conference deadlines, notes, reviews
│
├── scripts/                    # build + run, mirroring papers/ and templates/
│   ├── lib/latex_build.sh      #     the one build engine; every build.sh wraps it
│   ├── papers/<slug>/          #     build.sh (+ run_sim.sh, build.bat) per paper
│   ├── templates/<conference>/ #     build.sh per conference skeleton
│   ├── web/                    #     start.sh / stop.sh for the product
│   └── new-paper.sh            #     scaffold papers/<slug> + scripts/papers/<slug>
│
├── src/                        # the product: docbuilder, docserver, critic
├── web/                        # the product's React/Vite UI
└── tests/
```

Add a paper with `bash scripts/new-paper.sh <slug> [conference]` — it creates the
content directories *and* the build script, so the two trees stay in step.

---

## Requirements

### Windows

Install one of the following LaTeX distributions and ensure the `pdflatex` and
`bibtex` commands are available in your `PATH`:

- **TeX Live** (recommended, cross-platform): https://www.tug.org/texlive/
- **MiKTeX** (Windows-friendly): https://miktex.org/

To verify, open a Command Prompt and run:

```bat
pdflatex --version
bibtex --version
```

### WSL / Linux / macOS

Install TeX Live via your package manager. Inside WSL (Ubuntu/Debian):

```bash
# Minimal install
sudo apt install texlive-latex-base texlive-publishers texlive-science texlive-latex-extra

# Full install (includes all packages, ~5 GB)
sudo apt install texlive-full
```

To verify:

```bash
pdflatex --version
bibtex --version
```

> Host auto-install is **off by default**. Set `LATEX_AUTO_INSTALL=1` to let a
> build script `apt-get` the packages when `pdflatex` or `bibtex` are missing, or
> build with `LATEX_SANDBOX=docker`. Builds invoked through the doc server always
> run under the sandbox.

---

## Building

Every build — papers and conference skeletons alike — goes through one script,
`scripts/lib/latex_build.sh`. The per-target `build.sh` files are thin wrappers
over it, so they all behave the same and all take the same flags.

```bash
bash scripts/papers/apip/build.sh          # a paper     → papers/apip/latex/main.pdf
bash scripts/templates/ieee/build.sh       # a skeleton  → templates/latex/ieee/main.pdf
```

| Flag | Effect |
| --- | --- |
| `-c`, `--clean` | Delete `.aux/.bbl/.blg/.log/.out` first — use after editing `references.bib` or renaming a `\label` |
| `-q`, `--quiet` | Hide pdflatex/bibtex chatter; print only the summary |
| `-s DIR`, `--src DIR` | Build a different directory |
| `-h`, `--help` | Usage text |

Each run does the standard four-step compilation:

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `pdflatex main.tex` | First pass — generates aux files |
| 2 | `bibtex main` | Resolves bibliography references |
| 3 | `pdflatex main.tex` | Second pass — inserts citations |
| 4 | `pdflatex main.tex` | Third pass — resolves cross-references |

It then prints the page count and any undefined references, undefined citations,
or overfull boxes found in `main.log`. On failure, check `main.log` (LaTeX errors)
and `main.blg` (BibTeX errors) in the source directory.

**Windows:** only the APIP paper ships a batch equivalent,
`scripts\papers\apip\build.bat`. It takes the same flags but is standalone —
batch has no `source`, so it does not share the engine and must be updated
separately. Install [MiKTeX](https://miktex.org) or TeX Live for Windows first;
there is no auto-install path (that escape hatch is apt-specific).

### Per-conference notes

**NeurIPS** — the year-specific `.sty` is not bundled; the build downloads and
extracts it on first run and skips the download once present. Update these two
variables at the top of `scripts/templates/neurips/build.sh` each year:

```
STYLE_YEAR="2025"
STYLE_URL="https://media.neurips.cc/Conferences/NeurIPS2025/Styles.zip"
```

The current year's link is at `https://neurips.cc/Conferences/<YEAR>/PaperInformation/StyleFiles`.
Auto-download needs `curl` plus `unzip` (or Python 3 as fallback).

Note the style requires a **track option** alongside the mode — `main`,
`position`, `dandb`, `creativeai`, `sglblindworkshop` or `dblblindworkshop`.
Omitting it leaves `\@trackname` undefined and the build dies with "Undefined
control sequence".

**ACM** — `acmart.cls` (v2.03, Feb 2024) and its companion files are committed in
`templates/latex/acm/`; no TeX Live package or download is required. To update,
replace them with files from https://ctan.org/pkg/acmart. The default mode is
`sigconf` (two-column proceedings), correct for RecSys, SIGIR, CHI and most ACM
venues. Change the `\documentclass` option in `templates/latex/acm/main.tex`:

| Option | Use case |
|--------|----------|
| `sigconf` | ACM conference proceedings (default) |
| `manuscript` | Single-column review / preprint mode |
| `anonymous` | Add alongside `sigconf` for double-blind submission |

**AAAI** — `aaai2026.sty` and `aaai2026.bst` are committed in
`templates/latex/aaai/`; the build errors with instructions if they go missing.
This template always cleans aux files first, since a stale `main.aux` triggers
duplicate `\bibstyle` errors. To update for a new year: download the author kit,
extract `aaaiYYYY.sty`/`.bst` into `templates/latex/aaai/`, bump `STYLE_YEAR` in
`scripts/templates/aaai/build.sh`, and delete the old files.

**IEEE** — `IEEEtran.cls` and the `.bst` files are vendored (in
`templates/latex/_vendor/` and `templates/bibtex/`), so no IEEE TeX Live package
is needed.

---

## Adding Content

### A new paper

```bash
bash scripts/new-paper.sh <slug> [conference]     # conference defaults to ieee
```

Creates `papers/<slug>/{manuscript,latex,figures,deck}/` seeded from
`templates/latex/<conference>/`, plus `scripts/papers/<slug>/build.sh`. Drop your
`.docx` in `manuscript/`, put images in `figures/` (referenced by bare filename
via `\graphicspath`), and build with `bash scripts/papers/<slug>/build.sh`.

### A new section

Each section lives in its own file under `sections/` so collaborators can work in
parallel without merge conflicts on the root document.

1. Create `papers/<slug>/latex/sections/my_section.tex`
2. Add `\input{sections/my_section}` to `main.tex` at the desired position

Build artifacts (`.aux`, `.bbl`, `main.pdf`, …) are gitignored repo-wide — commit
sources, not output.

---

## Word ➜ LaTeX Conversion Pipeline

This repo now ships with a CLI and backend/frontend experiences for turning Word
manuscripts into venue-specific LaTeX workspaces.

### CLI usage

```
uv run papers convert manuscript.docx --template ieee --overwrite
```

Outputs land in `documents/<document_title>/` with the original `.docx`, copied
template files, generated `sections/*.tex`, `references/references.bib`, and an
optional PDF build (invokes `scripts/templates/<template>/build.sh`).

Key behaviors:

- Section boundaries come from Word heading styles (`Heading 1/2/3`, etc.)
- Figures are exported into `assets/` and inserted as LaTeX figure blocks
- A `manifest.json` tracks metadata for the backend/frontend

### FastAPI backend

```
uv run uvicorn docserver.main:app --reload
```

Endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/documents` | List all converted workspaces |
| `POST` | `/documents` | Upload a `.docx` + template name and kick off conversion |
| `GET` | `/documents/{id}` | Fetch manifest, sections, figures, build state |
| `GET` | `/documents/{id}/sections/{slug}` | Raw LaTeX for a section |
| `GET` | `/documents/{id}/pdf` | Download compiled PDF |
| `GET` | `/documents/{id}/word` | Download original Word file |
| `POST` | `/documents/{id}/compile` | Re-run LaTeX build |

The backend serves as the data source for the React UI and can power other
automation (CI, submissions, etc.).

### React document viewer

```
cd web
npm install
npm run dev
```

Set `VITE_API_BASE` (default `http://localhost:8000`) to point at the FastAPI
service. The UI provides:

1. Upload flow with template selection
2. Library of converted documents (per-template status, timestamps)
3. Section browser with LaTeX preview
4. PDF iframe preview + DOCX download tab

Build for production with `npm run build` (or `npx vite build`). Serve via
`npm run preview` or any static host.
