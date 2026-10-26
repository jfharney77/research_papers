# AGENTS.md — Research Paper Workspace (handoff)

Context doc for the next agent or session, whichever tool runs it (Claude Code, Devin, Codex,
Cursor, a human). `CLAUDE.md` is the Claude Code copy of the day-to-day working guidance and
is kept in sync with this file; if you are not Claude Code, read `CLAUDE.md` too, it has the
build commands and layout rules. End-user docs: `docs/guides/MANUAL.md`, `README.md`,
`docs/guides/DEPLOY-AWS.md`.

Ground rules for any agent:
- Work on **`devel-apip-camera-ready`** unless told otherwise. `devel-apip-6page` is frozen at
  the submitted version; do not edit it. Do not push to or merge into `main` without being asked.
- Run `uv run --group dev pytest` and `npm run build` (in `web/`) before claiming product code works.
- Commit with a one-line subject in the existing style (`APIP 6-page: …` for paper edits).
- The repo has two remotes: `origin` (GitHub) and `gitlab`. Push to `origin` unless told otherwise.

## What this project is
A **Word → LaTeX product**: upload a `.docx`, convert it to per-section LaTeX, build a
conference PDF (IEEE / NeurIPS / ACM / AAAI), edit + recompile, export, and **critique** the
writing. Web UI + CLI + REST API. The **APIP research** paper lives under `papers/apip/` and its
simulation under `sims/apip_sim/`; they are research content, not part of the product, and since
2026-09 they are where the active work is.

## Current status (2026-10-25)
- **Branch:** `devel-apip-camera-ready`, created 2026-10-25 from `devel-apip-6page` (`08e26f7`)
  for the ICA 2026 camera-ready revision. `devel-apip-6page` is the submission branch and is
  frozen; it is pushed to `origin`. Both contain `main`, `devel-apip-fullfeatures`, and
  `devel-apip-testbeds`; the `devel-reorg` restructuring is folded in (that local branch is gone;
  `origin/devel-reorg` still exists). `main` holds only the initial commit.
- **Working tree:** `IMPROVEMENT_SPEC_2026-09-11.md` at the repo root is untracked; it is a
  repo-wide improvement list (merge the devel branches, sandbox-escape tests, …). Decide whether
  to commit it or move it under `docs/specs/`.
- **Other branches:** `devel-apip-6page-seeds` (seed experiments), `devel-mesh-disruption`
  (a worktree, see `git worktree list`), `devel`, and on `origin` also `devel-apip` and
  `devel-apip-word2l`. None are merged.
- **Health:** Python test suite and web build were green as of the last product work (2026-08);
  no product code has changed since. Re-run both before touching `src/` or `web/`.

## The APIP paper (current focus)
The paper is "APIP" (an agent performance improvement protocol for agentic AI failure modes),
targeted at IEEE conference format. Two LaTeX versions exist under `papers/apip/latex/`:

| File | What it is | How to build |
| --- | --- | --- |
| `APIP_6page.tex` → `APIP_6page.pdf` | **The current version.** 6 pages, single self-contained file with an inline `thebibliography` (23 `\bibitem`s). Last edited 2026-09-15 (`bf572bd`). | `cd papers/apip/latex && pdflatex APIP_6page.tex && pdflatex APIP_6page.tex` |
| `main.tex` + `sections/` → `main.pdf` | The older 11-page per-section conversion of the Word manuscript. | `bash scripts/papers/apip/build.sh` |
| `APIP_full.tex`, `APIP_6page_SUBMIT*.tex` | Frozen snapshots (2026-09-03 and 2026-09-11). Do not edit. | same as 6-page |

Tag `apip-6page-singleseed-2026-09-13` (`49db339`) freezes the single-seed state of the paper
before the replication campaign.

Companion documents, read these before editing the paper:
- `papers/apip/CRITIQUE_2026-09-13.md` — adversarial review with keyed remedies
  (C1–C6 critical, M1–M11 major, D/P moderate). The 6-page commit log references these IDs
  ("closes D13", "C3's abstract half"), so check which are still open before re-raising one.
- `papers/apip/PREREGISTRATION_2026-09-14.md` — pre-registered seeds (21, 22, 23 for drift;
  13 for tool misuse) for the τ²-bench replication. All three drift seeds must be reported.
- `papers/apip/APIP_critique_revised_with_ChatGPT_additions.md` — earlier critique round.
- `papers/apip/manuscript/` — the Word sources; `papers/apip/deck/` — the slide deck.
- Run records referenced by the paper live outside this repo (sibling `../apip_simulations`
  and a Windows backup path named in the pre-registration).

Last run of edits (2026-09-10 to 09-15): abstract rewrite, Tier 3 compression to get back to
6 pages, and a widened generative-AI disclosure that now names ideation, compression, and the
model used.

**Venue: IEEE ICA 2026** (International Conference on Agentic AI, Kumamoto, Dec 14-17).

| Milestone | Date | State in this repo |
| --- | --- | --- |
| Abstract deadline | 2026-09-08 | done |
| Paper submitted | 2026-09-15 (the deadline) | `papers/apip/submissions/ICA2026_paper_238_submitted.pdf`; source `APIP_6page.tex` @ `bf572bd` on `devel-apip-6page` |
| Accepted | notified by 2026-10-15 | paper #238 |
| **Camera-ready due** | **2026-11-01** | in progress on `devel-apip-camera-ready`; final PDF goes to `papers/apip/submissions/ICA2026_paper_238_camera_ready.pdf` |
| Conference | 2026-12-14 to 17 | one-slide summary at `papers/apip/deck/APIP_ICA2026_summary.pptx` |

The submitted PDF carries the double-blind author block. Keep every submitted or camera-ready
PDF in `papers/apip/submissions/` (the `.gitignore` exempts that folder from the paper-PDF
rule). To see what changed since submission: `git diff bf572bd -- papers/apip/latex/APIP_6page.tex`.

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
- **Paper (now):** camera-ready for ICA 2026 by 2026-11-01. Replace the double-blind author
  block with real `\IEEEauthorblockN`/`\IEEEauthorblockA` entries, apply the reviewer-driven
  edits (the iteration in progress), re-check the IEEE camera-ready checklist (copyright
  notice, page limit, PDF eXpress if required), and save the final PDF to
  `papers/apip/submissions/`.
- **Paper:** add a `scripts/papers/apip/build_6page.sh` wrapper (or teach `build.sh` a `--src`
  for the single-file version) so the 6-page build is not a manual `pdflatex` invocation.
- **Repo:** push `devel-apip-camera-ready` as work lands; act on `IMPROVEMENT_SPEC_2026-09-11.md`
  item 1 (merge or retire the devel branches so `main` matches the documented layout).
- Review/triage the `docs/specs/CRITIQUE_SPEC*.md` notes (1–5) and reconcile with the implemented Critic.
- Smoke-test the real `docker build` + a live **Claude** critique end-to-end on AWS (only the
  offline `stub` provider was exercised locally).
- Reference extraction (`refextract.py`) is recent — confirm it's covered by tests.
- Sandbox-escape tests for `src/docbuilder/sandbox.py` (spec item 2 in the improvement spec).

## Cross-project note (this session, outside research_papers)
- A tailored `POWERPOINT_SPEC.md` (now `docs/specs/POWERPOINT_SPEC.md`) was created in **16 top-level `fable5` projects** (create-only,
  uncommitted in the other 15; committed here).
- A reusable **`github-aws-ecs`** skill was created at `~/.claude/skills/github-aws-ecs/SKILL.md`
  (GitHub Actions → AWS ECS Express Mode) and registered in the global `~/.claude/CLAUDE.md`.
