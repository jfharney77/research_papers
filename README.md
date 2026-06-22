# Research Paper Workspace

A **Word → LaTeX tool**: upload a `.docx` manuscript, convert it into per-section LaTeX,
build a conference-ready PDF (IEEE / NeurIPS / ACM / AAAI), and review/edit it in a web UI.

## Run it

```bash
python main.py            # product backend (FastAPI) on http://localhost:8000
scripts/start_web.sh      # backend + React dev server (http://localhost:5173)
papers convert paper.docx --template ieee   # CLI conversion
```

**Layout:** the product is `src/docbuilder` (converter + CLI), `src/docserver` (API),
`web/` (React), `latex/` + `script/latex/` (templates and build scripts). Unrelated
**research artifacts** — the APIP paper and its simulation app — live under `research/`
(run the simulation with `research/run_apip.sh`, port 8100).

**Security:** the LaTeX build runs sandboxed (no shell-escape, restricted file IO,
resource limits, timeout — see `src/docbuilder/sandbox.py`; `LATEX_SANDBOX=docker` for
container isolation). Set `DOCSERVER_API_KEY` to require auth, and `DOCSERVER_CORS_ORIGINS`
to allowlist browser origins.

---

## Repository Structure

```
research_papers/
├── latex/
│   ├── ieee/                   # IEEE conference template (IEEEtran)
│   │   ├── main.tex            # Root document
│   │   ├── references.bib      # Bibliography entries
│   │   └── sections/
│   │       ├── abstract.tex
│   │       ├── introduction.tex
│   │       ├── related_work.tex
│   │       └── conclusion.tex
│   ├── neurips/                # NeurIPS conference template
│   │   ├── main.tex            # Root document
│   │   ├── neurips_YYYY.sty    # Style file (auto-downloaded on first build)
│   │   ├── references.bib      # Bibliography entries
│   │   └── sections/
│   │       ├── abstract.tex
│   │       ├── introduction.tex
│   │       ├── related_work.tex
│   │       └── conclusion.tex
│   ├── acm/                    # ACM conference template (acmart/sigconf)
│   │   ├── main.tex            # Root document
│   │   ├── references.bib      # Bibliography entries
│   │   └── sections/
│   │       ├── abstract.tex
│   │       ├── introduction.tex
│   │       ├── related_work.tex
│   │       └── conclusion.tex
│   └── aaai/                   # AAAI conference template
│       ├── main.tex            # Root document
│       ├── aaaiYY.sty          # Style file (auto-downloaded on first build)
│       ├── aaaiYY.bst          # Bibliography style (auto-downloaded on first build)
│       ├── references.bib      # Bibliography entries
│       └── sections/
│           ├── abstract.tex
│           ├── introduction.tex
│           ├── related_work.tex
│           └── conclusion.tex
└── script/
    └── latex/
        ├── ieee/
        │   ├── build.bat       # Windows build script
        │   └── build.sh        # WSL / Linux / macOS build script
        ├── neurips/
        │   ├── build.bat       # Windows build script
        │   └── build.sh        # WSL / Linux / macOS build script
        ├── acm/
        │   ├── build.bat       # Windows build script
        │   └── build.sh        # WSL / Linux / macOS build script
        └── aaai/
            ├── build.bat       # Windows build script
            └── build.sh        # WSL / Linux / macOS build script
```

---

## Requirements

### Windows (build.bat)

Install one of the following LaTeX distributions and ensure the `pdflatex` and
`bibtex` commands are available in your `PATH`:

- **TeX Live** (recommended, cross-platform): https://www.tug.org/texlive/
- **MiKTeX** (Windows-friendly): https://miktex.org/

To verify, open a Command Prompt and run:

```bat
pdflatex --version
bibtex --version
```

### WSL / Linux / macOS (build.sh)

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

> The `build.sh` scripts will attempt to auto-install the required packages via
> `apt-get` if `pdflatex` or `bibtex` are not found.

---

## Building the IEEE Document

### Windows — using `build.bat`

#### Option 1 — Run from the repository root (recommended)

```bat
script\latex\ieee\build.bat
```

#### Option 2 — Run from inside the script directory

```bat
cd script\latex\ieee
build.bat
```

#### Option 3 — Pass a custom source path

```bat
script\latex\ieee\build.bat "C:\path\to\your\latex\ieee"
```

---

### WSL / Linux / macOS — using `build.sh`

#### Option 1 — Run from the repository root (recommended)

```bash
bash script/latex/ieee/build.sh
```

#### Option 2 — Make executable and run directly

```bash
chmod +x script/latex/ieee/build.sh
./script/latex/ieee/build.sh
```

#### Option 3 — Pass a custom source path

```bash
bash script/latex/ieee/build.sh /path/to/latex/ieee
```

> **WSL path tip:** Your Windows repository is typically accessible under
> `/mnt/c/Users/<username>/`. For example:
> ```bash
> cd /mnt/c/Users/jfhar/github/research_papers
> bash script/latex/ieee/build.sh
> ```

---

## Building the NeurIPS Document

### NeurIPS style file — auto-downloaded

NeurIPS provides a year-specific `.sty` file that is not bundled in this
repository. Both build scripts will **automatically download and extract it**
the first time they run. If the file is already present the download is skipped.

The download URL is stored in a variable at the top of each script:

```
# build.sh / build.bat
STYLE_YEAR="2025"
STYLE_URL="https://media.nips.cc/Conferences/2025/Styles/neurips_2025.zip"
```

**Update these two variables each year** when NeurIPS publishes new style files.
The current year's link can always be found at:
```
https://neurips.cc/Conferences/<YEAR>/PaperInformation/StyleFiles
```

Requirements for auto-download:
- **Windows:** `curl` (built into Windows 10 1803+)
- **WSL/Linux:** `curl` + `unzip` (or Python 3 as fallback)

---

### Windows — using `build.bat`

#### Option 1 — Run from the repository root (recommended)

```bat
script\latex\neurips\build.bat
```

#### Option 2 — Run from inside the script directory

```bat
cd script\latex\neurips
build.bat
```

#### Option 3 — Pass a custom source path

```bat
script\latex\neurips\build.bat "C:\path\to\your\latex\neurips"
```

---

### WSL / Linux / macOS — using `build.sh`

#### Option 1 — Run from the repository root (recommended)

```bash
bash script/latex/neurips/build.sh
```

#### Option 2 — Make executable and run directly

```bash
chmod +x script/latex/neurips/build.sh
./script/latex/neurips/build.sh
```

#### Option 3 — Pass a custom source path

```bash
bash script/latex/neurips/build.sh /path/to/latex/neurips
```

---

## Building the ACM Document

`acmart.cls` (v2.03, Feb 2024) and its companion files are committed directly
in `latex/acm/` — **no TeX Live package or separate download is required.**
To update to a newer version, replace the files in `latex/acm/` with those
from https://ctan.org/pkg/acmart.

The default mode is `sigconf` (two-column conference proceedings), which is
correct for venues like RecSys, SIGIR, CHI, and most ACM conferences. To switch
modes, change the `\documentclass` option in `latex/acm/main.tex`:

| Option | Use case |
|--------|----------|
| `sigconf` | ACM conference proceedings (default) |
| `manuscript` | Single-column review / preprint mode |
| `anonymous` | Add alongside `sigconf` for double-blind submission |

### Windows — using `build.bat`

#### Option 1 — Run from the repository root (recommended)

```bat
script\latex\acm\build.bat
```

#### Option 2 — Run from inside the script directory

```bat
cd script\latex\acm
build.bat
```

#### Option 3 — Pass a custom source path

```bat
script\latex\acm\build.bat "C:\path\to\your\latex\acm"
```

---

### WSL / Linux / macOS — using `build.sh`

#### Option 1 — Run from the repository root (recommended)

```bash
bash script/latex/acm/build.sh
```

#### Option 2 — Make executable and run directly

```bash
chmod +x script/latex/acm/build.sh
./script/latex/acm/build.sh
```

#### Option 3 — Pass a custom source path

```bash
bash script/latex/acm/build.sh /path/to/latex/acm
```

---

## Building the AAAI Document

### AAAI style files

`aaai2026.sty` and `aaai2026.bst` are already extracted and committed in
`latex/aaai/` — no download or extraction is needed to build.

The build scripts will error with instructions if the `.sty` file is ever
missing (e.g. after switching to a new year).

**To update for a new year:**
1. Download the new author kit from the AAAI website
2. Extract `aaaiYYYY.sty` and `aaaiYYYY.bst` into `latex/aaai/`
3. Update `STYLE_YEAR` and `STY_FILE` at the top of each build script:

```
STYLE_YEAR="2027"
STY_FILE="aaai2027.sty"
BST_FILE="aaai2027.bst"
```

4. Remove the old `.sty` and `.bst` from `latex/aaai/`

### Windows — using `build.bat`

#### Option 1 — Run from the repository root (recommended)

```bat
script\latex\aaai\build.bat
```

#### Option 2 — Run from inside the script directory

```bat
cd script\latex\aaai
build.bat
```

#### Option 3 — Pass a custom source path

```bat
script\latex\aaai\build.bat "C:\path\to\your\latex\aaai"
```

---

### WSL / Linux / macOS — using `build.sh`

#### Option 1 — Run from the repository root (recommended)

```bash
bash script/latex/aaai/build.sh
```

#### Option 2 — Make executable and run directly

```bash
chmod +x script/latex/aaai/build.sh
./script/latex/aaai/build.sh
```

#### Option 3 — Pass a custom source path

```bash
bash script/latex/aaai/build.sh /path/to/latex/aaai
```

---

### What the build scripts do

All build scripts run the same standard four-step LaTeX compilation process:

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `pdflatex main.tex` | First pass — generates aux files |
| 2 | `bibtex main` | Resolves bibliography references |
| 3 | `pdflatex main.tex` | Second pass — inserts citations |
| 4 | `pdflatex main.tex` | Third pass — resolves cross-references |

On success the output PDF is written to `main.pdf` inside the respective source
directory. If a step fails, check the relevant log file:

- `main.log` — LaTeX errors
- `main.blg` — BibTeX errors

---

## Adding Content

Each section lives in its own file under `sections/` so that collaborators can
work in parallel without merge conflicts on the root document.

To add a new section:

1. Create `latex/<conference>/sections/my_section.tex`
2. Add `\input{sections/my_section}` to `main.tex` at the desired position

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
optional PDF build (invokes `script/latex/<template>/build.sh`).

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
