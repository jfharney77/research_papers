# Spec: CI Build Matrix (tests, frontend, and every LaTeX document)

**Status:** Proposed
**Scope:** GitHub Actions workflows that run the test suite, the frontend build, and every
template and paper build on pull requests, plus a scheduled run that catches style-file rot.
No changes to the deploy pipeline (see §7).
**Branch:** implement on `devel-reorg`.

---

## 1. Summary & Goal

`.github/workflows/` contains exactly one workflow, `deploy-aws.yml`. It runs on
`workflow_dispatch` and on pushes to a `deploy-aws` branch, and it does nothing but build two
container images and update two ECS services. Nothing in the repository runs `pytest`, `npm run
build`, or any LaTeX build on a push or a pull request.

Two breakages sat undetected in the repository as a direct result, and were only found during the
`devel-reorg` reorganization when every template was built by hand:

1. **All four conference templates failed to build.** Each
   `templates/latex/<conf>/sections/figures.tex` pulled in
   `../../assets/figures/ai_architecture.png`, a repo-root `assets/` directory that has never
   existed in git history (`git log` and `git ls-tree` both confirm). ieee, neurips, acm and aaai
   all died with `Fatal error occurred, no output PDF file produced`. Fixed by moving the images
   to `templates/assets/figures/` and adding a `\graphicspath` to each `main.tex`.
2. **NeurIPS failed on a style-file requirement.** `neurips_2025.sty` builds its footer from
   `\@trackname`, which is only defined when a track option (`main`, `position`, `dandb`,
   `creativeai`, …) is passed alongside the mode. `main.tex` passed `[final]` alone and the build
   died with `Undefined control sequence`. A stale committed `main.pdf` from an older style
   version made the template look healthy. Fixed by passing `[final,main]`.

The second class of failure is time-dependent and will recur. `scripts/templates/neurips/build.sh`
downloads `neurips_<year>.sty` from `media.neurips.cc` on first build, and conference style files
are re-released annually with new requirements and new URLs. A repository that only builds when
someone happens to try will keep discovering this by accident, months late.

**Goal:** every pull request compiles every document in the repository and runs both test suites,
so a broken include path, a changed style-file contract, or a TypeScript error fails the PR
instead of the reorganization six months later. A weekly scheduled run repeats the LaTeX matrix
with the downloaded style files discarded, so upstream rot surfaces on its own.

---

## 2. Current Behavior (as-is)

| Check | Command | Runs in CI today |
|-------|---------|------------------|
| Python tests | `uv run --group dev pytest` (88 tests, ~0.3 s to collect; no TeX Live needed) | no |
| Frontend build | `npm run build` in `web/` (`tsc -b && vite build`) | no |
| Frontend lint | `npm run lint` in `web/` | no |
| Template builds | `bash scripts/templates/<conf>/build.sh` for ieee / neurips / acm / aaai | no |
| Paper builds | `bash scripts/papers/<slug>/build.sh`, currently only `apip` | no |
| Scaffolding | `bash scripts/new-paper.sh <slug> <conf>` | no |
| Container image build | `docker/backend.Dockerfile`, `web/Dockerfile` | only on the deploy branch |

Relevant existing pieces the workflows should build on rather than duplicate:

- **`scripts/lib/latex_build.sh`** — the shared build engine every `build.sh` wraps. It parses
  `-c/--clean`, `-q/--quiet`, `-s/--src`, checks for `pdflatex`/`bibtex`, runs
  `pdflatex → bibtex → pdflatex → pdflatex` with `-halt-on-error -interaction=nonstopmode`, and
  then greps `main.log` for `Undefined (control sequence|reference|citation)`,
  `LaTeX Warning: (Reference|Citation)` and `Overfull`, printing them as a text summary. It
  tolerates a nonzero `bibtex` (normal for a draft with no `\cite`) and always exits 0 once the
  passes succeed.
- **`src/docbuilder/templates.py`** — already discovers templates from the filesystem:
  a directory under `templates/latex/` containing `main.tex`, skipping `_`-prefixed names
  (`_vendor/` holds upstream author kits), flagged `buildable` when
  `scripts/templates/<id>/build.sh` exists. CI should use the same rules.
- **`docker/backend.Dockerfile`** — already installs the exact TeX Live package set the build
  scripts need (`texlive-latex-base`, `-recommended`, `-publishers`, `-latex-extra`,
  `-fonts-recommended`, `-science`, `-bibtex-extra`) plus `curl`/`unzip` for style-file fetching.
- **`.gitignore`** — now excludes `**/main.pdf` and `**/main.log`, so the stale-PDF masking that
  hid breakage 2 cannot recur. CI still needs to produce PDFs somewhere reviewable.

---

## 3. Proposed Changes

### a. TeX Live in CI: prebuilt image, not apt

TeX Live is the whole cost of this workflow. Three options:

| Approach | Cost | Verdict |
|----------|------|---------|
| `apt-get install` the package set in each job | ~4–6 min per job, paid once per matrix leg (5+ legs today, growing with `papers/`) | too slow; the matrix multiplies it |
| `actions/cache` over `/usr/share/texlive` + `/var/lib/dpkg` | brittle — dpkg state is not reliably restorable, and a partial restore fails in confusing ways | no |
| Prebuilt container image, jobs run with `container:` | one build, cached by the registry; matrix legs start in seconds | **yes** |

The package list already exists in `docker/backend.Dockerfile` and must not be forked. Split that
file at the apt layer with a named stage:

```dockerfile
FROM python:3.12-slim AS texlive
RUN apt-get update && apt-get install -y --no-install-recommends \
        texlive-latex-base ... curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

FROM texlive AS backend
RUN pip install --no-cache-dir uv
...
```

The deploy workflow is unaffected (`docker build -f docker/backend.Dockerfile .` still resolves to
the last stage). A new workflow **`.github/workflows/texlive-image.yml`** builds
`--target texlive` and pushes `ghcr.io/<owner>/research-papers-texlive:latest` on any change to
`docker/backend.Dockerfile`, on `workflow_dispatch`, and weekly (so security updates land).
LaTeX jobs then declare:

```yaml
container:
  image: ghcr.io/<owner>/research-papers-texlive:latest
```

with `LATEX_AUTO_INSTALL` left unset — `require_texlive` should find the toolchain already there,
and a failure to find it is a real signal that the image drifted from the package list.

### b. Dynamic matrix discovery

Both `templates/latex/` and `papers/` are meant to grow, and `scripts/new-paper.sh` adds to them
in pairs. A hardcoded `matrix.template: [ieee, neurips, acm, aaai]` would go stale the first time
someone scaffolds a paper — the same drift class this spec exists to close.

New **`scripts/ci/matrix.py`** (stdlib only, no `uv sync` needed) prints one JSON object:

```json
{
  "templates": ["aaai", "acm", "ieee", "neurips"],
  "papers": ["apip"],
  "problems": ["scripts/papers/ghost/build.sh has no papers/ghost/latex/main.tex"]
}
```

Discovery rules, deliberately mirroring `src/docbuilder/templates.py`:

- **Template:** a directory under `templates/latex/` whose name does not start with `_`, that
  contains `main.tex`, and that has a matching `scripts/templates/<id>/build.sh`. A template with
  `main.tex` but no build script is *not* an error — `templates.py` models that as
  `buildable=False` and the UI disables it — so it is emitted as a warning annotation and skipped.
- **Paper:** a directory under `papers/` containing `latex/main.tex` with a matching
  `scripts/papers/<slug>/build.sh`.
- **Problem:** a `scripts/papers/<slug>/build.sh` or `scripts/templates/<id>/build.sh` with no
  corresponding source directory. This one *is* an error: the script cannot possibly work.

A `discover` job runs it, writes the arrays to `$GITHUB_OUTPUT`, and fails on any `problems`
entry. Downstream jobs consume `fromJSON(needs.discover.outputs.templates)`.

### c. The PR workflow — `.github/workflows/ci.yml`

Triggers: `pull_request`, `push` to `main` and `devel-*`, and `workflow_dispatch`. A
`concurrency` group keyed on the ref with `cancel-in-progress: true` so superseded PR runs stop.
`permissions: contents: read`.

| Job | Runs on | Does | Blocks merge |
|-----|---------|------|--------------|
| `discover` | `ubuntu-latest` | `python3 scripts/ci/matrix.py` → outputs | yes (on `problems`) |
| `python` | `ubuntu-latest` | `astral-sh/setup-uv`, `uv sync --group dev`, `uv run --group dev pytest -q` | yes |
| `web` | `ubuntu-latest` | `actions/setup-node` with `cache: npm`, `npm ci`, `npm run build` in `web/` | yes |
| `web-lint` | `ubuntu-latest` | `npm run lint` in `web/`, `continue-on-error: true` | no |
| `templates` | texlive container, `matrix.template` from `discover` | `bash scripts/templates/${{ matrix.template }}/build.sh -c -q` | yes |
| `papers` | texlive container, `matrix.paper` from `discover` | `bash scripts/papers/${{ matrix.paper }}/build.sh -c -q` | yes |
| `scaffold` | texlive container | `bash scripts/new-paper.sh ci-smoke ieee` then build the result | yes |

`-c` (clean) is right for CI: the workspace is fresh anyway, and it makes the run independent of
any aux file that slipped past `.gitignore`. `-q` keeps the log readable; the full `main.log` is
uploaded regardless.

No `paths:` filters. Filtering the LaTeX matrix to PRs that touch `.tex` files would have hidden
breakage 1 exactly as effectively as having no CI at all — that break came from a directory move,
not a `.tex` edit. With a prebuilt image each leg is roughly a minute; run them all.

`timeout-minutes: 10` on every LaTeX job. A `pdflatex` waiting on an interactive prompt is the
classic way to burn a runner hour, and `-interaction=nonstopmode` is not a guarantee.

### d. `scripts/new-paper.sh` round trip

The `scaffold` job is the smoke test for the scaffolder, and it is worth having because a broken
`new-paper.sh` is silent until someone starts a paper:

```bash
bash scripts/new-paper.sh ci-smoke ieee
bash scripts/papers/ci-smoke/build.sh -c -q
test -f papers/ci-smoke/latex/main.pdf
```

Then assert the tree is otherwise untouched (`git status --porcelain` lists only the new
`papers/ci-smoke/` and `scripts/papers/ci-smoke/` paths). On PRs it runs once with the default
`ieee`; the scheduled run does it across every discovered template, since seeding from a template
is the operation most likely to break when a style file changes.

### e. Artifacts

Every LaTeX job uploads:

- `main.pdf` as `pdf-template-<id>` / `pdf-paper-<slug>`, `if: always()`, retention 14 days.
  Reviewers get the rendered output attached to the run instead of building locally, which
  matters most for the papers.
- `main.log` as `log-<kind>-<id>`, `if: failure()`. The engine's text summary is enough for a
  warning; a hard failure needs the file.

A final `summarize` job (`if: always()`) writes a `$GITHUB_STEP_SUMMARY` table of
document / status / page count / warning count, parsed from the per-job outputs. Page count is
already extracted by `latex_build` from `Output written on main.pdf (N page`.

### f. Warning severity

`latex_build` already greps four warning classes out of `main.log`. Their CI severity:

| Signal | Severity | Reasoning |
|--------|----------|-----------|
| `pdflatex` nonzero exit | **block** | `-halt-on-error` means a real error. This is breakage 1 and 2. |
| `main.pdf` missing after the last pass | **block** | The "no output PDF file produced" case. Must be checked explicitly — a nonzero `bibtex` is tolerated by design, so absence of the PDF is the ground truth. |
| `Undefined control sequence` in `main.log` | **block** | Breakage 2's signature. Normally already fatal under `-halt-on-error`; treat a survivor as a failure anyway. |
| `Undefined reference` / `Citation undefined` | **warn** | A draft with a `\label` not yet written is a legitimate in-progress state, and papers live in this repo mid-write. Blocking here would train people to skip CI. |
| `Overfull \hbox` | **warn** | Typography, and a submission-time concern rather than a correctness one. Templates ship with some. |
| A style file that downloads but produces a different `.sty` version | **warn on PR, block on schedule** | See §3g. |

To make this machine-readable, `scripts/lib/latex_build.sh` gains two small additions, both
no-ops outside CI:

1. After the fourth pass, fail if `main.pdf` is absent (`echo` + `exit 1`), regardless of
   `GITHUB_ACTIONS`. This is a correctness improvement for humans too.
2. When `GITHUB_ACTIONS` is set, re-emit the warning summary as `::warning file=...::` annotations
   and `::error::` for the blocking classes, so they land on the PR's Files-changed view instead
   of only in the raw log.

Explicitly **not** proposed: comparing warning counts against the base branch to flag *new*
warnings. That needs a baseline store and produces noise on rebases. See §7.

### g. The scheduled workflow — `.github/workflows/latex-nightly.yml`

Weekly (`schedule: cron` Monday early UTC) plus `workflow_dispatch`. Same matrix, same container,
with three differences:

1. **Discard downloaded style files before building.** Delete `templates/latex/neurips/neurips_*.sty`
   so `scripts/templates/neurips/build.sh` exercises its download path against
   `STYLE_URL` (`https://media.neurips.cc/Conferences/NeurIPS<year>/Styles.zip`) for real. This is
   the only check that catches a re-released style file, a moved URL, or a changed option
   contract — the failure mode that produced breakage 2.
2. **Check the documented fallback URLs are alive.** A step issues `curl -sIf --max-time 30`
   against `STYLE_URL` and against the URLs printed in the acm/aaai "missing style file" errors.
   A 404 here is a failure even if the build passes on the vendored copy, because the error
   message is now lying to whoever hits it.
3. **Report loudly.** On failure, open (or comment on an existing) GitHub issue titled
   `Scheduled LaTeX build failure` with the failing legs and a run link. Requires
   `permissions: issues: write`. A red X on a schedule with nobody watching is how this rot goes
   unnoticed a second time.

The scheduled run also flips the "style file version changed" signal from warn to block — an
annual style release should stop the world once, be fixed deliberately, and not sit in a warning
list.

---

## 4. Files Affected (implementation reference)

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | **new** — discover / python / web / templates / papers / scaffold / summarize |
| `.github/workflows/latex-nightly.yml` | **new** — scheduled matrix with style files discarded, URL liveness check, issue on failure |
| `.github/workflows/texlive-image.yml` | **new** — build `--target texlive` and push to GHCR on Dockerfile change + weekly |
| `docker/backend.Dockerfile` | name the apt layer `AS texlive`; add `FROM texlive AS backend`. No behavior change for the deploy path. |
| `scripts/ci/matrix.py` | **new** — filesystem discovery of templates and papers, JSON out, drift detection |
| `scripts/lib/latex_build.sh` | fail when `main.pdf` is missing; emit GitHub annotations when `GITHUB_ACTIONS` is set |
| `scripts/README.md` | document what CI runs and how to reproduce a failing leg locally |

`.github/workflows/deploy-aws.yml` is untouched.

---

## 5. Reproducing CI Locally

Every CI step is a command that already works from a checkout, which is the point of routing
through `scripts/lib/latex_build.sh`:

```bash
uv run --group dev pytest                       # the python job
( cd web && npm ci && npm run build )           # the web job
bash scripts/templates/neurips/build.sh -c      # one templates leg
bash scripts/papers/apip/build.sh -c            # one papers leg
python3 scripts/ci/matrix.py                    # what the matrix will expand to
```

To reproduce the container environment exactly:

```bash
docker build -f docker/backend.Dockerfile --target texlive -t rp-texlive .
docker run --rm -v "$PWD:/w" -w /w rp-texlive bash scripts/templates/neurips/build.sh -c
```

---

## 6. Verification Plan

- **Unit:** `scripts/ci/matrix.py` on the current tree emits the four templates and `apip`;
  a temporary `templates/latex/_scratch/main.tex` is skipped; a `templates/latex/x/main.tex`
  with no build script is warned about, not listed; a `scripts/papers/ghost/build.sh` with no
  `papers/ghost/` makes it exit nonzero.
- **Workflow:** open a draft PR and confirm all seven jobs appear, that the matrix legs are named
  after the discovered ids, and that the run finishes in a few minutes rather than the ~25 an
  apt-per-leg install would take.
- **E2E:** re-introduce breakage 1 on a branch — point one template's `figures.tex` back at
  `../../assets/figures/ai_architecture.png` — and confirm that template's leg fails with
  "no output PDF file produced", that `main.log` is uploaded, and that the PR cannot be merged.
- **E2E:** re-introduce breakage 2 — change `\usepackage[final,main]{neurips_2025}` back to
  `[final]` — and confirm the neurips leg fails on `Undefined control sequence` while the other
  three legs stay green, proving the matrix isolates documents.
- **E2E:** scaffold a paper on a branch (`bash scripts/new-paper.sh probe acm`), push, and confirm
  a `papers (probe)` leg appears in the run with no workflow edit, and that its PDF is downloadable
  from the run's artifacts.
- **E2E:** run `latex-nightly.yml` via `workflow_dispatch`, confirm `neurips_2025.sty` is
  re-downloaded from `media.neurips.cc` during the run and the build still passes.
- **Edge:** point `STYLE_URL` at a 404 on a branch and dispatch the scheduled workflow; confirm the
  URL-liveness step fails and an issue is opened.
- **Edge:** a PR that introduces an overfull box and an undefined reference passes, with both
  surfaced as annotations and counted in the step summary.
- **Edge:** a PR touching only `web/` still runs the full LaTeX matrix (no path filters), and a PR
  touching only `docker/backend.Dockerfile` also triggers `texlive-image.yml`.
- **Edge:** two pushes to the same PR in quick succession — the first run is cancelled by the
  concurrency group rather than both completing.
- **Edge:** delete the GHCR image tag and re-run; the LaTeX jobs fail fast with a pull error rather
  than silently falling back to a host without TeX Live.

---

## 7. Non-Goals

- **The deploy pipeline.** `deploy-aws.yml` already exists and works. This spec does not gate
  deploys on CI, add environments, or change the ECS steps. Wiring `needs: [python, web]` into the
  deploy workflow is a reasonable follow-up, but it is a separate decision.
- **Publishing PDFs anywhere but run artifacts.** No GitHub Pages site, no release attachments, no
  committing built PDFs (`.gitignore` deliberately excludes `**/main.pdf` now, and a stale
  committed PDF is what masked breakage 2).
- **Warning regression tracking.** No baseline of warning counts per document and no "this PR adds
  three overfull boxes" gate. Warnings are reported, not diffed.
- **Testing the docserver's own build path end to end** (upload a `.docx` → `POST /documents`
  → PDF). The sandbox has its own environment assumptions; covering it belongs in the test suite,
  not the matrix.
- **Other CI providers, self-hosted runners, or matrix expansion across OS/Python versions.** One
  Linux runner and one Python version match how this project is deployed.
- **Auto-updating style files.** The scheduled job reports that NeurIPS re-released; a human bumps
  `STYLE_YEAR` and fixes the option list.
