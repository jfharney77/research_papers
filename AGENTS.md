# AGENTS.md — Research Paper Workspace (handoff)

Context doc for the next agent/session. For day-to-day working guidance see `CLAUDE.md`;
for end-user docs see `docs/guides/MANUAL.md`, `README.md`, and `docs/guides/DEPLOY-AWS.md`.

## What this project is
A **Word → LaTeX product**: upload a `.docx`, convert it to per-section LaTeX, build a
conference PDF (IEEE / NeurIPS / ACM / AAAI), edit + recompile, export, and **critique** the
writing. Web UI + CLI + REST API. The unrelated **APIP research** paper and simulation live under
`research/` and are not part of the product.

## Current status (2026-06-28)
- **Branch:** `devel-apip-fullfeatures` (this is where all the work lives; never merged to `main`).
  There are **unpushed commits** on it — push when ready.
- **Working tree:** `docs/specs/CRITIQUE_SPEC_5.md` is a design note added outside a session.
- **Health:** Python test suite (`uv run --group dev pytest`) and the web build (`npm run build`)
  were green as of the last feature work; both container images build and run under Podman.

## What's been built (session arc, newest concepts last)
1. **Dynamic template selection** — backend registry (`src/docbuilder/templates.py`) discovers
   `latex/*/` templates with build scripts; `GET /templates` drives the UI dropdown. `f79513f`
2. **Tests + Recompile button + build-log surfacing** (`GET /documents/{id}/log`). `6961c90`
3. **Section editing** (`PUT …/sections/{slug}`), **LaTeX `.zip` export** (`…/archive`), and
   **storage hardening** (filename sanitization, malformed-manifest skip). `3a888cf`
4. **Build sandbox + auth + product/research split** — `src/docbuilder/sandbox.py` (no shell-escape,
   restricted TeX file IO, rlimits, timeout; `LATEX_SANDBOX=docker` option); API-key auth
   (`src/docserver/auth.py`) + scoped CORS; APIP moved to `research/`; `main.py` is the single
   entry point. `2db555b`
5. **The Critic** — `src/critic/`: per-section 3 criticisms + AI-genericness score (hybrid
   heuristics + LLM) + de-AI tips; providers `stub` (default, offline) / `claude` / `ollama` /
   `cerebras`; endpoints `GET /critic/providers`, `POST|GET /documents/{id}/critique`,
   `POST /critic/adhoc`. Built from `docs/specs/SPEC-critic-button.md`. `d89cd2b`
6. **AWS deployment** — `docker/backend.Dockerfile` (Python + TeX Live), `web/Dockerfile`,
   `.github/workflows/deploy-aws.yml` (OIDC → ECR → ECS Express Mode), `docs/guides/DEPLOY-AWS.md`. `0707c56`
7. **Claude provider wired into the image** (`--extra llm`; `CRITIC_PROVIDER`/`ANTHROPIC_API_KEY`
   on the service). `4631f01`
8. **Frontend image fix** — `npm ci` → `npm install` for the Vite 8 / rolldown native binding;
   both images verified with Podman. `7bf7537`
9. **`docs/guides/MANUAL.md`** — full user guide. `1d569b5`
10. **Reference extraction** — `src/docbuilder/refextract.py` + `references_warning` on the
    document model/response/UI (`docs/specs/CRITIQUE_SPEC.md` line of work). Recent commits.
11. **PowerPoint deck builder** — `scripts/build_deck.py` generates a `.pptx` from `docs/specs/POWERPOINT_SPEC.md`.
    Recent commits.

## How to run / test / deploy
```bash
uv sync                       # deps (add --extra llm for the Claude critic)
./scripts/web/start.sh        # backend :8000 + React dev :5173   (scripts/web/stop.sh to stop)
python main.py                # backend only (single entry point)
uv run --group dev pytest     # tests
npm run build                 # in web/ — type-check + build the frontend
```
Deploy: follow `docs/guides/DEPLOY-AWS.md` (ECR + two ECS roles + OIDC role → set GitHub vars/secrets → push
`deploy-aws` branch). Both Dockerfiles build with Docker or Podman.

## Layout & conventions
- Product: `src/docbuilder` (converter, CLI, sandbox, templates, refextract), `src/docserver`
  (FastAPI), `src/critic`, `web/` (React/Vite).
- Research content, split by kind: `templates/` (LaTeX + Word styles), `papers/<slug>/`
  (`manuscript/` · `latex/` · `figures/` · `deck/`), `sims/` (supporting code), `docs/`
  (`specs/` · `guides/` · `research/`). `scripts/` mirrors it — `scripts/papers/<slug>/` and
  `scripts/templates/<conf>/` are thin wrappers over `scripts/lib/latex_build.sh`. Scaffold a
  paper with `bash scripts/new-paper.sh <slug> [conference]`.
- **src layout, no build backend** — run with `PYTHONPATH=src` (tests set it via
  `pyproject.toml`; `main.py` and `scripts/web/start.sh` set it).
- **Auth:** when `DOCSERVER_API_KEY` is set, all routes except `/health` require it (Bearer /
  `X-API-Key` / `?api_key=`); the frontend bakes `VITE_DOCSERVER_TOKEN` at build time.
- **Runtime data:** `documents/<id>/` (manifest, workspace, PDF, `critique.json`) — git-ignored and
  **ephemeral** in containers (use EFS/S3 for persistence).
- Key env vars: `DOCSERVER_API_KEY`, `DOCSERVER_CORS_ORIGINS`, `LATEX_SANDBOX`, `LATEX_BUILD_TIMEOUT`,
  `LATEX_AUTO_INSTALL`, `CRITIC_PROVIDER`, `ANTHROPIC_API_KEY` (see `docs/guides/MANUAL.md` §7).

## Open items / suggested next steps
- **Push** the unpushed commits on `devel-apip-fullfeatures`; consider a PR → `main`.
- Review/triage the `docs/specs/CRITIQUE_SPEC*.md` notes (1–5) and reconcile with the implemented Critic.
- Smoke-test the real `docker build` + a live **Claude** critique end-to-end on AWS (only the
  offline `stub` provider was exercised locally).
- Reference extraction (`refextract.py`) is recent — confirm it's covered by tests.

## Cross-project note (this session, outside research_papers)
- A tailored `POWERPOINT_SPEC.md` (now `docs/specs/POWERPOINT_SPEC.md`) was created in **16 top-level `fable5` projects** (create-only,
  uncommitted in the other 15; committed here).
- A reusable **`github-aws-ecs`** skill was created at `~/.claude/skills/github-aws-ecs/SKILL.md`
  (GitHub Actions → AWS ECS Express Mode) and registered in the global `~/.claude/CLAUDE.md`.
