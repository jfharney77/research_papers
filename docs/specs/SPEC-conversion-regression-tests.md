# Spec: Conversion Regression Tests (real manuscripts + "does it compile")

**Status:** Proposed
**Scope:** Test suite only. No converter behavior changes, no fixes to the extraction gaps the
new fixtures expose (see §7).
**Branch:** implement on `devel-reorg`.

---

## 1. Summary & Goal

The suite is 88 tests and passes in 4.6s (`uv run --group dev pytest`). Two bugs that broke the
LaTeX build for every real manuscript survived all 88 of them:

1. **Unicode punctuation.** `text_to_latex()` in `src/docbuilder/utils.py` escaped the ten LaTeX
   specials and passed everything else through. `papers/apip/manuscript/APIP_Paper_v8_tracked.docx`
   contains 150 non-ASCII characters — 65 em dashes (U+2014), 55 right single quotes (U+2019), 13
   en dashes (U+2013), 4 minus signs (U+2212), smart double quotes, `×`, `†`, NBSP, `±`. pdflatex
   rejects most of them ("Unicode character ... not set up for use with LaTeX") and the build dies
   on pass 1. Fixed by `_UNICODE_PUNCTUATION` in `utils.py`.
2. **Empty bibliography.** `src/docbuilder/refextract.py` extracts zero references from that
   document, so `references.bib` is empty, so bibtex emits `\begin{thebibliography}{}` with no
   `\bibitem` and pdflatex fails with "Something's wrong--perhaps a missing \item". Fixed by the
   `has_references=False` branch in `_rewrite_main` (`src/docbuilder/converter.py`).

Both were found by hand: convert the project's own paper, then try to compile the result.

The common cause is not a missing assertion in one test file. Every existing test asserts on the
**shape of a generated string** — `test_converter.py` checks which `\input{}` lines appear in
`main.tex`, `test_refextract.py` checks BibTeX field text — and the fixtures are synthetic `.docx`
files built in memory with python-docx using clean `Heading 1` styles and plain ASCII prose. Two
things are absent:

- No test compiles the generated LaTeX. The build is the actual acceptance criterion and nothing
  exercises it.
- No fixture resembles a real Word document. Synthetic input cannot produce smart quotes, tracked
  changes, `Normal`-styled headings, or an unparseable reference list, because the test author has
  to type those in deliberately, and if they knew to type them in they would have already fixed the
  bug.

**Goal:** add a regression layer with three parts — a compile test that runs the real build engine,
a character-coverage test that runs without TeX, and a small corpus of adversarial fixtures modelled
on what real documents actually contain — while keeping the default `pytest` run at its current
few-second cost.

---

## 2. Current Behavior (as-is)

| Test file | What it covers | Fixture style |
|-----------|----------------|---------------|
| `tests/test_converter.py` | `_rewrite_main` / `_copy_template` string invariants | a hand-written `main.tex` string constant |
| `tests/test_refextract.py` | Sources XML + heuristic paragraph parsing | in-memory `Document()`, ASCII text |
| `tests/test_critic.py` | Critic providers and scoring | in-memory `Document()` |
| `tests/test_templates.py` | template registry / `buildable` | filesystem only |
| `tests/test_workspace.py`, `test_concurrency.py`, `test_auth.py` | API surface | `monkeypatch` + `TestClient` |
| `tests/test_sandbox.py` | `run_sandboxed` limits | shell commands, no TeX |

There is no `tests/conftest.py`, no `tests/fixtures/`, and no marker configuration. `pyproject.toml`
has only:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Facts confirmed against the four shipped manuscripts (all tracked in git):

| File | Size | Paragraphs | Tables | Non-ASCII chars | Extracted refs |
|------|------|-----------|--------|-----------------|----------------|
| `APIP_Paper_v3.docx` | 29 KB | 175 | 3 | 129 | 0 |
| `APIP_Paper_v6.docx` | 35 KB | 215 | 5 | 153 | 0 |
| `APIP_Paper_v7_tracked.docx` | 35 KB | 224 | 5 | 147 | 0 |
| `APIP_Paper_v8_tracked.docx` | 49 KB | 226 | 5 | 150 | 0 |

v8 paragraph styles: 188 `Normal`, 23 `Heading 2`, 9 `Heading 1`, 6 `List Paragraph`; its XML holds
21 `<w:ins>` and 2 `<w:del>` elements. All four extract **zero** references, so every one of them
hits the empty-bibliography path.

Relevant machinery that already exists and must be reused rather than reimplemented:

- `scripts/lib/latex_build.sh` — the shared build engine (arg parsing, `require_texlive`,
  `pdflatex → bibtex → pdflatex → pdflatex`, warning report). The per-template wrappers under
  `scripts/templates/<id>/build.sh` are thin and source it.
- `src/docbuilder/sandbox.py` `run_sandboxed()` — timeout, rlimits, no shell-escape, restricted TeX
  file IO; `LATEX_SANDBOX=docker` swaps in a container.
- `src/docbuilder/converter.py` `_run_build()` — already wires the two together and records
  `build.status` / `build.log` in `manifest.json`.

A compile test therefore only has to call `convert_document(..., build_pdf=True)` and assert on the
manifest and the artifacts.

---

## 3. Proposed Changes

### a. Real-manuscript fixture

Two options, and the tradeoff is size and provenance:

**Option A — point at `papers/apip/manuscript/` directly.** No new bytes in the repo; the files are
already tracked, and they are the project's own work, so there is no third-party licensing question
(never commit someone else's `.docx` as a fixture). The cost is coupling: `papers/` is a research
artifact directory that the paper work rewrites and reorganizes, so a manuscript revision can fail
the converter tests for reasons that have nothing to do with the converter, and a moved directory
breaks collection.

**Option B — commit a dedicated small fixture.** A 5–10 KB `.docx` built once from a trimmed copy of
the manuscript, frozen under `tests/fixtures/`. Stable, cheap, diff-free, and it can be built to
contain exactly the pathologies we care about. The cost is that it stops being real: once frozen, it
only ever contains the messiness we already knew to include, which is precisely the failure mode
this spec exists to fix.

**Recommendation: both, with one indirection.** In `tests/conftest.py`:

```python
REAL_MANUSCRIPTS = sorted((REPO_ROOT / "papers" / "apip" / "manuscript").glob("*.docx"))
CANONICAL_MANUSCRIPT = REPO_ROOT / "papers" / "apip" / "manuscript" / "APIP_Paper_v8_tracked.docx"
```

- Tests that need *a* real document use `CANONICAL_MANUSCRIPT` (v8: newest, largest, tracked
  changes, tables, the full punctuation set).
- The cheap character-coverage scan (§3c) runs over **all** of `REAL_MANUSCRIPTS`, parametrized, so
  adding a v9 automatically widens coverage at no maintenance cost.
- Both are wrapped in `pytest.mark.skipif(not path.exists(), ...)` so the suite stays green if
  `papers/` is reorganized or the manuscripts are pulled out of the repo.
- Golden files (§3e) are **not** generated from the real manuscripts — they would churn on every
  revision. Real documents get property assertions ("output is ASCII", "it compiles"); golden files
  are reserved for the frozen synthetic fixtures.

If `papers/` ever leaves the repo, the fix is one line: repoint the two constants at a frozen copy
under `tests/fixtures/`. That is Option B, deferred until it is needed.

### b. "Does it compile" test — `tests/test_build_smoke.py`

The single most valuable test here. Marked `@pytest.mark.latex`, skipped cleanly when the toolchain
is absent:

```python
requires_texlive = pytest.mark.skipif(
    not (shutil.which("pdflatex") and shutil.which("bibtex")),
    reason="TeX Live (pdflatex + bibtex) not installed",
)
```

Note it checks for the binaries, not for a marker or an env var: `require_texlive` in
`latex_build.sh` exits 1 with a clear message when they are missing, and `LATEX_AUTO_INSTALL`
defaults to 0, so without this guard the test would fail rather than skip on a bare machine.

The test body drives the production path end to end:

```python
monkeypatch.setattr(converter, "DOCUMENTS_ROOT", tmp_path)   # never write into repo documents/
manifest = converter.convert_document(
    CANONICAL_MANUSCRIPT,
    ConversionOptions(template="ieee", build_pdf=True, overwrite=True),
)
```

`DOCUMENTS_ROOT` is a module-level constant imported into `converter`, so it is patched on the
converter module — the same technique `tests/test_workspace.py` already uses for `storage`.

Assertions:

1. `manifest.json` records `build.status == "succeeded"` (this is where the empty-bibliography bug
   would have surfaced: status `failed`).
2. `<workspace>/ieee/main.pdf` exists, begins with `%PDF-`, and has ≥ 1 page via `pypdf` (already a
   runtime dependency).
3. `build.log` contains none of: `Unicode character`, `perhaps a missing \item`, `! LaTeX Error`,
   `! Undefined control sequence`. This is the assertion that names the two known bugs, and the log
   is the artifact to attach to the failure message.
4. On failure, the assertion message includes the last ~40 lines of `build.log`. A bare
   `assert status == "succeeded"` is useless for diagnosis.

Constraints and reuse:

- The build goes through `_run_build` → `run_sandboxed` → `scripts/templates/ieee/build.sh` →
  `scripts/lib/latex_build.sh`. The test invokes **none** of `pdflatex`, `bibtex`, or the shell
  script directly. If the build engine changes, the test follows for free.
- `LATEX_BUILD_TIMEOUT` defaults to 120s and `LATEX_CPU_SECONDS` to 60s; leave them alone so the
  test measures the same limits production uses. A four-pass build of a 12-page IEEE paper is
  ~10–20s, which is why this test is marker-gated (§3f).
- `LATEX_SANDBOX` is read at import time in `config.py`, so a docker-backend variant needs the env
  var set before import. Out of scope: the smoke test runs whatever backend the environment
  configures, and a second `@pytest.mark.docker` variant can be added later.
- One template (`ieee`) by default. A parametrized `test_all_templates_compile` over
  `ieee/acm/neurips/aaai` carries an extra `@pytest.mark.slow`; NeurIPS downloads its `.sty` on
  first build, so that one additionally skips when the network is unavailable.

### c. Character coverage — `tests/test_unicode_coverage.py`

Fast, no TeX required, and it is the test that would have caught bug #1 in under a second. Three
layers:

1. **Map self-consistency.** Every value in `_UNICODE_PUNCTUATION` is itself pure ASCII, and every
   key is non-ASCII. A replacement that smuggles in another Unicode character is a silent no-op.
2. **Converted output is ASCII.** Convert `CANONICAL_MANUSCRIPT` with `build_pdf=False` (fast: no
   TeX), then walk `main.tex`, every `sections/*.tex`, and `references.bib`, asserting every
   character is `ord(ch) < 128`. The failure message lists each offending character with its
   codepoint, a count, and one surrounding snippet — so the fix is "add this row to the map", not
   "go read a 226-paragraph document".
3. **Source-side sweep, parametrized over all four manuscripts.** Collect every non-ASCII character
   in `paragraph.text` (plus table cell text) and assert each one is a key in
   `_UNICODE_PUNCTUATION`. This is the cheap early-warning version of layer 2: it needs no
   conversion at all and it flags a new glyph the moment a new manuscript revision lands.

Layers 2 and 3 stay unmarked and run by default; together they cost well under a second.

An allowlist parameter (default empty) covers the case where a template legitimately needs a UTF-8
character. Keep it empty until something actually needs it.

### d. Empty-bibliography regression — extend `tests/test_converter.py`

Unit level (no TeX): `_rewrite_main(ws, sections, title=..., has_references=False)` comments out
both `\bibliographystyle{...}` and `\bibliography{...}` with the `% [no references extracted]`
prefix, leaves them intact when `has_references=True`, and still splices the section inputs at the
right position in both cases. The existing tests call `_rewrite_main` without the flag, so the
default-`True` path is covered but the `False` path — the shipped bug — is not.

Integration level (no TeX): convert `CANONICAL_MANUSCRIPT` with `build_pdf=False`, assert
`references.bib` contains no `@`, `manifest.references_warning` is non-`None`, and `main.tex` has no
uncommented `\bibliography` line. Under `@pytest.mark.latex`, the §3b smoke test proves the same
workspace compiles.

### e. Golden files

Golden files apply only to the frozen adversarial fixtures (§3g), where the input never changes.

Layout: `tests/golden/<fixture_name>/<template>/main.tex` and `.../sections/*.tex`.

Mechanics:

- A `assert_matches_golden(actual_dir, golden_dir)` helper in `tests/conftest.py` compares the file
  set and the text of each file, reporting mismatches with `difflib.unified_diff` — a raw
  `assert a == b` on a 200-line `.tex` file is unreadable.
- Regeneration: a `--regen-golden` flag registered via `pytest_addoption` in `conftest.py`. With it
  set, the helper writes the actual output over the golden files and marks the test skipped rather
  than passed, so a regen run can never be mistaken for a green run. Documented in `AGENTS.md` as
  `uv run --group dev pytest --regen-golden` followed by `git diff tests/golden/` — the diff review
  *is* the test.
- Determinism is a precondition. `manifest.json` carries `build.last_run` timestamps and
  `source_docx` paths, so it is excluded from golden comparison; assert on its fields directly
  instead. Section slugs derive from headings and are deterministic. If any generated `.tex` ever
  embeds a date, it must be normalized in the helper before comparison.
- Golden files are only worth it where output is large and structural. For a three-line assertion,
  write the assertion.

### f. Markers and default runtime

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = [
    "latex: needs a TeX Live toolchain (pdflatex + bibtex); runs a real build",
    "slow: takes more than a couple of seconds",
    "realdoc: reads the manuscripts under papers/apip/manuscript/",
]
addopts = "-m 'not latex'"
```

The default `pytest` run therefore stays at ~5s and never shells out to pdflatex. Opt in with:

```bash
uv run --group dev pytest -m latex      # only the build tests
uv run --group dev pytest -m ""         # everything, including builds
```

The `-m ""` form is the part worth documenting, because `addopts` deselection is otherwise
invisible: someone running plain `pytest` on a box with TeX Live installed will not notice the
compile tests are being skipped. Two mitigations: name the marker in the `AGENTS.md` verification
section, and have CI run `-m ""` on the job that has TeX Live in the image.

Note the redundancy is deliberate — the tests are both marker-gated *and* `skipif`-guarded on the
binaries, so `-m latex` on a machine without TeX skips cleanly instead of failing.

### g. Adversarial synthetic fixtures — `tests/fixtures/docx_factory.py`

Builder functions returning a written `.docx` path, each modelling one thing real documents do that
the current fixtures do not. Where python-docx has no API (tracked changes, OMML), the fixture
splices raw XML into the paragraph element — that is exactly what makes these fixtures worth having,
since no clean python-docx call can produce them.

| Fixture | What it models | Assertion |
|---------|----------------|-----------|
| `normal_styled_headings` | headings as bold `Normal` paragraphs, not `Heading 1` | `_build_from_docx`'s `style_name.startswith("Heading")` gate never fires, so the whole paper collapses into the single `ensure_section()` fallback. Assert exactly that (≥ 1 section, no crash, no text lost) — this is documented current behavior, not a bug fix. |
| `tracked_changes` | `<w:ins>` and `<w:del>` runs | Verified on v8: python-docx's `Paragraph.text` skips runs nested inside `<w:ins>`, so inserted words vanish (the real document renders "the agent is the subject, not the , of the plan"). Assert the known-lost text with `@pytest.mark.xfail(strict=True)` so the gap is recorded and the test flips to a pass the day extraction is fixed. |
| `with_table` | a 3×3 table | The converter iterates `docx.paragraphs` only, so all 5 tables in v8 are dropped silently. Assert the current behavior plus the absence of a crash; the xfail records that content is lost. |
| `with_equation` | an OMML `<m:oMath>` block | No crash, and no raw XML or namespace prefix leaks into the `.tex`. |
| `with_footnotes` | a footnote reference | No crash, no stray reference marker in the body text. |
| `empty_bibliography` | body text, no References heading | `references.bib` empty, `\bibliography` commented, `references_warning` set; compiles under `latex`. |
| `unicode_soup` | every key of `_UNICODE_PUNCTUATION` plus all ten LaTeX specials, in one paragraph | Output is pure ASCII; compiles under `latex`. This is the fixture that makes bug #1 impossible to reintroduce. |
| `pathological_headings` | headings containing `&`, `%`, `_`, `$`, an em dash; a duplicate heading title; an empty heading | Slugs are unique and non-empty; heading text is escaped. |

The `unicode_soup` and `empty_bibliography` fixtures also get a `latex`-marked compile test — they
are small, so both builds together add a few seconds to the opt-in run.

Fixtures are built into `tmp_path` at test time rather than committed as binaries: the builder code
is reviewable in a diff, a `.docx` is not.

---

## 4. Test Inventory (what gets added)

| Test | Marker | Cost | Catches |
|------|--------|------|---------|
| `test_unicode_map_values_are_ascii` | — | ~0 | a bad map entry |
| `test_converted_output_is_ascii[v8]` | `realdoc` | <1s | **bug #1** |
| `test_source_chars_are_all_mapped[v3,v6,v7,v8]` | `realdoc` | <1s | an unmapped glyph in a new revision |
| `test_rewrite_main_comments_bibliography_when_empty` | — | ~0 | **bug #2** (unit) |
| `test_real_manuscript_has_no_active_bibliography` | `realdoc` | <1s | **bug #2** (integration) |
| `test_real_manuscript_compiles` | `latex`, `realdoc` | ~15s | both, plus anything else that breaks the build |
| `test_unicode_soup_compiles`, `test_empty_bib_compiles` | `latex` | ~5s | regressions in the two fixes, without needing `papers/` |
| `test_all_templates_compile[4]` | `latex`, `slow` | ~60s | template-specific breakage |
| adversarial fixture tests (§3g) | — | <1s | crashes and silent data loss on messy input |
| golden-file tests for the synthetic fixtures | — | <1s | unintended changes to generated LaTeX |

Default `pytest`: still a few seconds. `pytest -m ""` on a TeX Live box: roughly a minute and a
half.

---

## 5. Files Affected (implementation reference)

| File | Change |
|------|--------|
| `tests/conftest.py` | **new** — `REAL_MANUSCRIPTS` / `CANONICAL_MANUSCRIPT`, `requires_texlive`, `assert_matches_golden`, `--regen-golden` option, `tmp_documents_root` fixture |
| `tests/fixtures/docx_factory.py` | **new** — the eight adversarial builders |
| `tests/test_unicode_coverage.py` | **new** — §3c |
| `tests/test_build_smoke.py` | **new** — §3b |
| `tests/test_real_manuscript.py` | **new** — no-TeX assertions over the real document (sections extracted, ASCII output, bibliography state) |
| `tests/test_adversarial_docx.py` | **new** — §3g |
| `tests/golden/` | **new** — checked-in expected `.tex` for the synthetic fixtures |
| `tests/test_converter.py` | add the `has_references=False` cases |
| `pyproject.toml` | `markers` + `addopts` |
| `AGENTS.md` / `CLAUDE.md` | document `pytest -m ""` and `--regen-golden` in the verification steps |

No file under `src/` changes.

---

## 6. Verification Plan

- **Unit:** `uv run --group dev pytest` still finishes in a few seconds and reports the new
  no-TeX tests; the count rises from 88 with no failures.
- **Regression proof:** revert `_UNICODE_PUNCTUATION` to `{}` — `test_converted_output_is_ascii`
  and `test_real_manuscript_compiles` must both fail. Revert the `has_references` branch in
  `_rewrite_main` — `test_rewrite_main_comments_bibliography_when_empty` and
  `test_real_manuscript_compiles` must both fail. A regression suite that does not fail against the
  original bugs is not a regression suite; run this check before merging.
- **E2E:** `uv run --group dev pytest -m ""` on a machine with TeX Live: converts
  `APIP_Paper_v8_tracked.docx`, builds `main.pdf`, and the PDF opens with a real title and body
  text (spot-check once by hand; the test only asserts page count).
- **E2E:** `./scripts/web/start.sh`, upload the same `.docx` through the UI, confirm the build
  status matches what the test reports — the test path and the product path must agree because they
  share `_run_build`.
- **Edge:** temporarily rename `pdflatex` off `PATH`; `pytest -m latex` reports skips, not
  failures, and plain `pytest` is unaffected.
- **Edge:** rename `papers/apip/manuscript/` away; all `realdoc` tests skip with a clear reason and
  the synthetic fixture tests still cover both bugs.
- **Edge:** run with `LATEX_BUILD_TIMEOUT=1`; the smoke test fails with `build.status == "failed"`
  and the timeout message in the log, confirming the assertion reads the real sandbox result rather
  than an assumed one.
- **Edge:** `pytest --regen-golden` reports skips (never passes) and produces a reviewable
  `git diff` under `tests/golden/`.

---

## 7. Non-Goals

- **Fixing what the fixtures expose.** Tables, equations, footnotes, tracked-change insertions, and
  `Normal`-styled headings are all mishandled or dropped today. This spec pins the current behavior
  with tests (`xfail(strict=True)` where content is lost) so the gaps are recorded and measurable.
  Each fix is its own change.
- **Improving reference extraction.** All four manuscripts yield zero references. That is a real
  product problem and a separate spec; here it is only the input to the empty-bibliography path.
- **PDF content or visual verification.** The compile tests assert the build succeeds and the PDF
  has pages. No pixel diffing, no text extraction from the PDF, no layout checks.
- **Running every template on every build test.** One canonical template by default; the
  four-template sweep is `slow`-marked.
- **Third-party document corpora.** Only manuscripts this project owns get committed.
- **CI configuration.** This spec defines the markers and the opt-in command; wiring a TeX Live
  image into a pipeline is separate.
