# Research Paper Workspace — User Manual

A tool that turns a **Word (`.docx`) manuscript into per-section LaTeX**, builds a
conference-ready **PDF** (IEEE / NeurIPS / ACM / AAAI), lets you **edit sections and
recompile**, **export the LaTeX**, and **critique** the writing (per-section criticism +
an "AI-genericness" score). It has a web UI, a CLI, and a REST API.

> The unrelated **APIP research** paper and simulation live under `research/` and are not
> part of this product — see [§9](#9-the-research-folder).

---

## 1. Prerequisites

| Need | Why |
|------|-----|
| **Python 3.12** + [`uv`](https://docs.astral.sh/uv/) | backend + CLI |
| **Node.js 20+** and `npm` | the web frontend |
| **TeX Live** (`pdflatex`, `bibtex`) | building PDFs locally |

TeX Live install (Debian/WSL): `sudo apt install texlive-latex-base texlive-latex-recommended
texlive-publishers texlive-latex-extra texlive-fonts-recommended texlive-science`.
You can convert without it (`--no-build` / `build_pdf=false`) and add it later, or build in a
container (see [§7](#7-configuration-environment-variables)).

---

## 2. Install & run

```bash
uv sync                     # install dependencies (add --extra llm for the Claude critic)

# Option A — full stack (backend :8000 + React dev server :5173)
./scripts/web/start.sh
./scripts/scripts/web/stop.sh       # stop both

# Option B — backend only
python main.py              # http://localhost:8000  (single entry point)

# Tests
uv run --group dev pytest
```

Open **http://localhost:5173** for the UI (Option A), or the API at **http://localhost:8000**
(`/docs` for interactive Swagger).

---

## 3. The web UI — typical workflow

1. **Upload** a `.docx` in the top form and pick a **Template** (the dropdown is populated
   from the server; non-buildable templates are disabled). Click **Convert** — the document is
   split into sections and a PDF is built. If a workspace with that name exists you'll be asked
   to **Overwrite**.
2. The document appears in the left **Workspace** list. Select it to open the viewer tabs:
   - **PDF** — the built PDF (or the build-failure message + *View build log*).
   - **LaTeX** — pick a section in the tree to view/**edit** its `.tex`; **Save** writes it back.
   - **WORD** — download the original `.docx` or **Download LaTeX (.zip)** (the full source).
   - **LOG** — the `pdflatex`/`bibtex` build output.
   - **CRITIC** — see [§5](#5-the-critic).
   - **↻ Recompile** — rebuild the PDF after editing sections.
   - **Delete** — remove the workspace.
3. Edit a section → **Save** → **Recompile** → check the **PDF** tab. Repeat. **Download** the
   PDF or the LaTeX zip when done.

---

## 4. The CLI

Convert a document from the command line (no server needed):

```bash
PYTHONPATH=src uv run python -m docbuilder.cli convert paper.docx --template ieee
PYTHONPATH=src uv run python -m docbuilder.cli convert paper.docx -t neurips --no-build
```

- `--template/-t` — one of `ieee`, `acm`, `neurips`, `aaai` (validated; bad names list the valid ones).
- `--no-build` — skip the PDF build (just produce the LaTeX workspace).

Output lands in `documents/<document_id>/` (see [§8](#8-where-things-live-on-disk)).

---

## 5. The Critic

Generates, **per section**, three criticisms (with suggestions), an **AI-genericness score
(0–100)**, the signals behind it, and **de-AI rewrite tips**. The score blends deterministic
text heuristics (filler phrases, sentence-length burstiness, transition density, rule-of-three,
em-dashes) with a language-model judgment.

- **In the UI:** open the **CRITIC** tab on a document → **Run Critic** (cached afterward;
  **↻ Re-run** forces a fresh pass). The gauge is colored green (<35) / amber (35–65) / red (>65).
- **Ad-hoc:** the sidebar **"Critique a file (PDF/DOCX)"** input critiques any uploaded PDF or
  `.docx` without creating a workspace.

**Providers** (set `CRITIC_PROVIDER`):

| Provider | Notes |
|----------|-------|
| `stub` (default) | Offline, deterministic — works with no credentials. |
| `claude` | Anthropic `claude-opus-4-8`. Needs `uv sync --extra llm` (or the dep in the image) + `ANTHROPIC_API_KEY`. |
| `ollama` | Local model; set `CRITIC_OLLAMA_URL` (Windows-host gateway IP from WSL, not localhost) + `CRITIC_OLLAMA_MODEL`. |
| `cerebras` | `gpt-oss-120b`; set `CEREBRAS_API_KEY`. |

If a configured provider can't be reached, the Critic **degrades to the stub** rather than failing.

---

## 6. The REST API

Base URL `http://localhost:8000`. When `DOCSERVER_API_KEY` is set, every route except `/health`
and the docs requires the key as `Authorization: Bearer <key>`, `X-API-Key: <key>`, or `?api_key=<key>`.

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness (no auth). |
| `GET /templates` | Available templates + default. |
| `POST /documents?template=&build_pdf=&overwrite=` | Upload a `.docx`, convert, (optionally) build. |
| `GET /documents` · `GET /documents/{id}` · `DELETE /documents/{id}` | List / fetch / remove workspaces. |
| `GET /documents/{id}/sections` · `GET\|PUT /documents/{id}/sections/{slug}` | List / read / save a section's LaTeX. |
| `POST /documents/{id}/compile` | Rebuild the PDF. |
| `GET /documents/{id}/pdf` · `/word` · `/archive` · `/log` | Download PDF / original docx / LaTeX zip / build log. |
| `GET /critic/providers` | Providers + the active one. |
| `POST\|GET /documents/{id}/critique` (`?refresh=true`) | Run / fetch the cached critique. |
| `POST /critic/adhoc` | Critique an uploaded PDF/`.docx`. |

Example:

```bash
curl -F file=@paper.docx "http://localhost:8000/documents?template=ieee&build_pdf=true"
curl http://localhost:8000/documents/<id>/pdf -o paper.pdf
```

Interactive docs at `http://localhost:8000/docs`.

---

## 7. Configuration (environment variables)

**Server**

| Variable | Default | Meaning |
|---|---|---|
| `DOCSERVER_API_KEY` | (unset) | If set, requires the key on all routes (except `/health`). Unset = auth disabled (dev only). |
| `DOCSERVER_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed browser origins. |
| `DOCSERVER_HOST` / `DOCSERVER_PORT` | `0.0.0.0` / `8000` | Bind address/port for `python main.py`. |

**LaTeX build sandbox** — the build runs constrained because it compiles untrusted input:

| Variable | Default | Meaning |
|---|---|---|
| `LATEX_SANDBOX` | `local` | `local` (rlimits + restricted file IO + timeout) or `docker` (container). |
| `LATEX_BUILD_TIMEOUT` | `120` | Wall-clock seconds before a build is killed. |
| `LATEX_CPU_SECONDS` / `LATEX_MAX_MEMORY_MB` / `LATEX_MAX_OUTPUT_MB` | `60` / `2048` / `50` | Resource caps. |
| `LATEX_AUTO_INSTALL` | `0` | `1` lets the build scripts `apt-get install` TeX Live on the host. |
| `LATEX_DOCKER_IMAGE` | `texlive/texlive:latest` | Image used when `LATEX_SANDBOX=docker`. |

**Critic** — `CRITIC_PROVIDER`, `CRITIC_CLAUDE_MODEL`, `ANTHROPIC_API_KEY`, `CRITIC_OLLAMA_URL`,
`CRITIC_OLLAMA_MODEL`, `CRITIC_CEREBRAS_URL`, `CRITIC_CEREBRAS_MODEL`, `CEREBRAS_API_KEY`, `CRITIC_TIMEOUT`.

**Frontend (build-time only, baked into the bundle)** — `VITE_API_BASE` (backend URL),
`VITE_DOCSERVER_TOKEN` (must equal `DOCSERVER_API_KEY` when auth is on).

---

## 8. Where things live on disk

```
documents/<document_id>/
├── manifest.json            # title, template, sections, build status
├── <original>.docx          # the uploaded manuscript
├── critique.json            # cached Critic result (if run)
└── <template>/              # the LaTeX workspace
    ├── main.tex             # rewritten to \input each section
    ├── sections/<slug>.tex  # one file per section (editable)
    ├── references/, assets/
    ├── main.pdf             # build output
    └── build.log
```

`document_id` is the snake-cased filename stem. `documents/` is git-ignored and **ephemeral** in
container deployments (see `DEPLOY-AWS.md` in this folder for persistence).

---

## 9. The research folders

Separate from the product, split by kind — `templates/` (LaTeX and Word styles), `papers/`
(one directory per paper: `manuscript/`, `latex/`, `figures/`, `deck/`), `sims/` (supporting
code, including the APIP simulation launched by `scripts/papers/apip/run_sim.sh` on **:8100**),
and `docs/` (specs, guides, conference deadlines). Build any paper with
`bash scripts/papers/<slug>/build.sh`; start a new one with `bash scripts/new-paper.sh <slug>`.
Touch these only for the research artifacts, not the tool.

---

## 10. Deployment

Containerized deployment to **AWS ECS** via GitHub Actions is documented in **`docs/guides/DEPLOY-AWS.md`**
(Dockerfiles in `docker/backend.Dockerfile` and `web/Dockerfile`; workflow in
`.github/workflows/deploy-aws.yml`). Both images build with Docker or Podman.

---

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| Convert fails: *"Template '…' has no build script"* | Use a valid template, or `--no-build`, or install TeX Live. |
| Build status **failed** | Open the **LOG** tab / `GET /documents/{id}/pdf` 404 → read `build.log`. Often a missing LaTeX package — install the `texlive-*` set or use `LATEX_SANDBOX=docker`. |
| Build **timed out** | Raise `LATEX_BUILD_TIMEOUT`/`LATEX_CPU_SECONDS`. |
| UI shows **401 / Failed to fetch** | `DOCSERVER_API_KEY` is set but the frontend wasn't built with a matching `VITE_DOCSERVER_TOKEN`; or the origin isn't in `DOCSERVER_CORS_ORIGINS`. |
| "Workspace exists" on upload | Choose **Overwrite**, or delete the old workspace first. |
| Critic shows provider **stub** unexpectedly | The configured provider failed (missing dep/key/host) and fell back — check `CRITIC_PROVIDER`, `ANTHROPIC_API_KEY`, and that `anthropic` is installed (`uv sync --extra llm`). |
| "Failed to fetch" in the UI generally | Confirm the backend is up: `curl http://localhost:8000/health` and `tail -f logs/backend.log`. |
