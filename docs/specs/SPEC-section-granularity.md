# Spec: Section File Granularity (Word → LaTeX converter)

**Status:** Proposed
**Scope:** Heading-depth policy for splitting a `.docx` into `sections/*.tex`, the file naming
that follows from it, and abstract handling. No change to the build pipeline, the section
editing API surface, or the templates themselves (see §8).
**Branch:** `devel-reorg`.

---

## 1. Summary & Goal

`src/docbuilder/converter.py` writes one `.tex` file per Word heading, at every heading level.
The project's own manuscript, `papers/apip/manuscript/APIP_Paper_v8_tracked.docx`, has 32
headings (9 `Heading 1`, 23 `Heading 2`), so a conversion produces **33 section files** — one
per heading plus one for the front matter that precedes the first heading. The same paper,
converted by hand into `papers/apip/latex/sections/`, is **10 files**.

The stated reason for per-section files is parallel writing without merge conflicts on the root
document (`README.md` §"A new section", `templates/README.md`). One file per H2 does not serve
that: `4-2-phase-2-cause-attribution.tex` is four paragraphs that nobody edits independently of
the phase list around it, and the resulting 33-line `\input{}` block in `main.tex` cannot be
read as an outline of the paper.

**Goal:** split on **`Heading 1` only** by default, emitting deeper headings inline as
`\subsection` / `\subsubsection` inside their parent's file. Make the depth configurable
(`ConversionOptions` field → CLI flag → API query param) for authors who genuinely want finer
files. Fix the naming and abstract handling that the current per-heading split exposes.

On the real manuscript this yields **10 files** — `abstract.tex` plus one per H1 — matching the
count a human arrived at independently.

---

## 2. Current Behavior (as-is)

| Layer | File | Behavior |
|-------|------|----------|
| Split point | `converter.py` → `_build_from_docx()` | Every paragraph whose style name starts with `Heading` flushes the buffer and opens a new `SectionEntry` + new file. Depth is never consulted for the split decision. |
| Depth | `converter.py` → `_heading_level()` | Parses `"Heading 2"` → `2`. Used only by `_latex_heading()` to choose the LaTeX command, never to decide whether to start a file. |
| Naming | `converter.py` → `slugify(text or f"section-{order}")` | Slug is the heading text with non-alphanumerics collapsed to `-`. There is **no generated numeric prefix** — the leading digits in `2-1-agent-evaluation-…` come from the Word heading text itself (`"2.1  Agent Evaluation…"`). |
| Ordering | `models.py` → `SectionEntry.order` | Already a 1-based sequence number in document order; `_rewrite_main()` sorts by it. Not used in filenames. |
| Front matter | `converter.py` → `ensure_section()` | Paragraphs before the first heading get a synthetic section titled `"Section 1"`, file `section-1.tex`. |
| Abstract | template `main.tex` | Templates carry `\input{sections/abstract}` under an `% ---- Abstract ----` marker. `_copy_template()` deletes the placeholder `sections/abstract.tex` and `_SECTION_INPUT_RE` strips the `\input`, so a converted document has **no abstract at all**. |
| Root doc | `converter.py` → `_rewrite_main()` | Emits one `\input{sections/<slug>}` per `SectionEntry`, in `order`, as a flat block. |
| API | `src/docserver/main.py` | `GET/PUT /documents/{id}/sections/{slug}` addresses one file per slug. `SectionResponse.level` is returned but the UI (`web/src/App.tsx` ~line 499) renders a flat `<ol>` — 33 buttons, no nesting. |

Reproduce with `bash scripts/word_to_latex.sh` (writes `papers/apip/latex.imported/`, leaves the
hand-edited `papers/apip/latex/` alone), then `diff -rq papers/apip/latex papers/apip/latex.imported`.

**Defects this exposes, all visible in the current output:**

1. **33 files at mixed nesting.** `2-background-and-related-work.tex` and its four children are
   peers on disk and peers in the `\input` list; nothing records that they nest.
2. **Word's numbering leaks into the slug and the printed heading.**
   `2-background-and-related-work.tex` contains `\section{2  Background and Related Work}`, which
   IEEEtran renders as "II. 2 Background and Related Work". The template numbers sections itself.
3. **Empty headings become empty files.** The manuscript has one blank `Heading 2`; it produces
   an empty `section-8.tex` and a stray `\input{sections/section-8}`.
4. **Author-side numbering errors become filenames.** A mis-numbered heading (`"2.  Team
   Dynamics…"` sitting between §2.4 and §3) produces `2-team-dynamics-….tex`, which sorts
   directly beside the H1 `2-background-….tex` in a directory listing.
5. **No abstract.** The manuscript's abstract is plain body text in `section-1.tex`, along with
   the title and author block, which the template already typesets — so the converted PDF repeats
   the title in the body and never uses `\begin{abstract}`.
6. **Slug collisions are silent.** Two headings with the same text produce the same slug; the
   second `_write_section_file()` overwrites the first and `main.tex` inputs it twice.

---

## 3. Design

### a. Heading-depth policy

Add `section_depth: int = 1` to `ConversionOptions`. During the paragraph walk, a heading
starts a new file only when `_heading_level(style) <= section_depth`. Deeper headings do **not**
flush the buffer; they append `_latex_heading(level, text)` to the current file, exactly as a
body paragraph would.

- `section_depth=1` (default) — one file per H1. Nine files for the APIP manuscript, plus the
  abstract.
- `section_depth=2` — files for H1 and H2, H3+ inlined.
- `section_depth=3` — the practical equivalent of today's behavior for this manuscript.

Valid range is `1..3`; anything outside raises `ConversionError` (converter), exits 1 (CLI), or
returns HTTP 400 (API), matching how `template` is validated today.

A deeper heading arriving with no file open (a document that opens on `Heading 2`) calls the
existing `ensure_section()` path, so content is never dropped.

Blank headings at any level are skipped — no file, no `SectionEntry`, no `\subsection{}`.

`_latex_heading()` needs no change: it already maps 1/2/≥3 to
`\section`/`\subsection`/`\subsubsection`.

### b. Naming

Two properties are in tension. The hand-written names are *semantic* (`case_study.tex`,
`open_problems.tex`); the generated ones are *positional* (`3-a-taxonomy-of-agent-failure-modes.tex`).
Semantic names cannot be derived reliably — nothing in the manuscript maps
"6 Illustrative Case Study: Aria at RetailCo" to `case_study`. Guessing produces worse names than
the heading text, so **keep deriving the slug from the heading text**, and fix what is actually
broken about it:

1. **Strip the author's own leading numbering** from the heading text before slugifying *and*
   before emitting `\section{}`. A regex on the heading text — leading digits, optional
   dot-separated groups, optional trailing `.`/`)`, then whitespace — turns
   `"2.1  Agent Evaluation and the Deployment Gap"` into
   `"Agent Evaluation and the Deployment Gap"`. This fixes defect 2 (the doubled number in the
   PDF) and defect 4 (the author's numbering mistakes reaching the filesystem) at once.
   Only strip when what remains is non-empty, so a heading that is literally `"4.2"` keeps its
   text.

2. **Add a generated ordinal prefix** from `SectionEntry.order`, zero-padded to two digits:
   `01-abstract.tex`, `02-introduction.tex`, … `10-conclusion.tex`. The prefix is *generated*,
   not scraped, so it stays consistent when the author renumbers headings in Word, it makes a
   directory listing read in document order, and it makes filename collisions impossible.

The prefix becomes part of `slug` (and therefore `section_id`, `latex_path`, and the section
URL path), not a separate field — the API addresses sections by slug and one identifier is
easier to keep consistent than two. `SectionEntry.order` stays as-is and remains the sort key
for `_rewrite_main()`; the prefix is a rendering of it, not a replacement.

Slug uniqueness is guaranteed by the prefix, but keep a defensive de-duplication (`-2`, `-3`
suffix) so a future change that drops the prefix cannot silently reintroduce defect 6.

### c. Abstract

Templates already have an abstract slot; the converter should fill it rather than delete it.

- If a heading (at any level) normalizes to `abstract`, its content becomes
  `sections/<NN>-abstract.tex`, wrapped in `\begin{abstract} … \end{abstract}`.
- If no such heading exists, scan the paragraphs before the first heading for one whose text is
  exactly `Abstract` (case-insensitive) — which is how the APIP manuscript marks it — and treat
  the paragraphs from there to the first heading as the abstract.
- Whatever precedes the abstract marker (title, author block, review notice) is written to
  `sections/frontmatter.tex` but **not** `\input` by `main.tex`. The template typesets its own
  title and author block; keeping the file preserves the content for the author without printing
  it twice.
- If neither rule matches, no abstract file is written and the marker stays empty — today's
  behavior, minus the front-matter dump into the body.

`_rewrite_main()` gains a `has_abstract` path: when an abstract entry exists, its `\input` is
placed at the template's `% ---- Abstract ----` marker (or immediately after `\maketitle` if the
marker is absent) rather than in the auto-generated body block, and it is excluded from that
block. The abstract `SectionEntry` keeps `order=1` so it is still first in the manifest and the
UI.

### d. Manifest and API

`SectionEntry` stays **one entry per file**; the `GET`/`PUT` section endpoints keep addressing
exactly one file per slug, so no API semantics change. `level` continues to record the heading
level of the file's own heading — under the default policy it is `1` for every entry, which is
the point.

Two additive fields:

- `SectionEntry.subheadings: list[str] = []` — the titles of the headings inlined into this
  file, in order. This is what lets the UI show an outline without splitting files, and it makes
  the depth policy auditable from the manifest alone.
- `DocumentManifest.section_depth: int | None = None` — the depth used for this conversion.
  `None` means "converted before this spec" (see §5).

`ConversionOptions.section_depth` is threaded through `convert_upload()`
(`src/docserver/storage.py`) from a new `section_depth: int = 1` query parameter on
`POST /documents`, and through `--section-depth/-D` on `docbuilder.cli convert`.

`rebuild_pdf()` does not re-split — it only recompiles what is on disk — so it needs no change.

### e. Frontend

`web/src/App.tsx` renders `subheadings` as a nested, non-clickable `<ul>` under each section
button. Clicking the parent opens the one file that contains them. The upload form does not need
a depth control; the default is right for a conference paper, and the flag exists for the CLI.

---

## 4. API Contract

`POST /documents?template=ieee&build_pdf=true&overwrite=false&section_depth=1`

`section_depth` is optional, defaults to `1`, and must be `1..3`; out of range returns
HTTP 400 with the valid range, in the same style as the template validation.

`GET /documents/{id}` and `GET /documents/{id}/sections` gain `subheadings` on each section and
`section_depth` on the document:

```json
{
  "section_depth": 1,
  "sections": [
    { "section_id": "01-abstract", "title": "Abstract", "level": 1, "slug": "01-abstract",
      "latex_path": "sections/01-abstract.tex", "order": 1, "subheadings": [] },
    { "section_id": "03-background-and-related-work", "title": "Background and Related Work",
      "level": 1, "slug": "03-background-and-related-work",
      "latex_path": "sections/03-background-and-related-work.tex", "order": 3,
      "subheadings": ["Agent Evaluation and the Deployment Gap",
                      "The Performance Improvement Plan as a Structural Template",
                      "Kirkpatrick's Four-Level Evaluation Framework",
                      "AI Governance and Documentation Requirements",
                      "Team Dynamics, Membership Change, and Coordination"] }
  ]
}
```

Both fields are additive; existing clients that ignore them keep working.

---

## 5. Migration & Back-Compat

Workspaces under `documents/` are runtime scratch — the directory is gitignored and holds
converted uploads, not sources. Nothing is rewritten in place:

- `DocumentManifest.section_depth` defaults to `None`, so manifests written before this change
  still parse. `None` is displayed as "legacy" and means the workspace has one file per heading.
- `SectionEntry.subheadings` defaults to `[]`, so old entries parse unchanged.
- Old workspaces keep their old slugs; `GET`/`PUT` on those slugs keep working, and
  `rebuild_pdf()` keeps compiling their existing `main.tex`. Re-splitting an existing workspace
  is out of scope — re-upload with `overwrite=true` to get the new layout.
- `papers/apip/latex/` (hand-edited, 10 files) is not touched by any of this. The comparison
  target is `papers/apip/latex.imported/`, which `scripts/word_to_latex.sh` regenerates and which
  should drop from 33 files to 10.

---

## 6. Files Affected (implementation reference)

| File | Change |
|------|--------|
| `src/docbuilder/converter.py` | `section_depth` on `ConversionOptions`; depth check at the split point in `_build_from_docx()`; strip leading heading numbers; ordinal slug prefix; skip blank headings; abstract detection + `\begin{abstract}` wrap; front-matter file; `_rewrite_main()` abstract placement |
| `src/docbuilder/models.py` | `SectionEntry.subheadings`; `DocumentManifest.section_depth` |
| `src/docbuilder/utils.py` | heading-number stripping helper (regex lives beside `slugify`) |
| `src/docbuilder/cli.py` | `--section-depth/-D`, validated with the same error style as `--template` |
| `src/docserver/main.py` | `section_depth` query param on `POST /documents`, 400 on out-of-range |
| `src/docserver/storage.py` | thread `section_depth` through `convert_upload()` |
| `src/docserver/schemas.py` | mirror the two new fields |
| `web/src/App.tsx` | render `subheadings` nested under each section |
| `templates/README.md`, `README.md` | state the policy: one file per top-level section |

---

## 7. Verification Plan

- **Unit (depth):** synthetic doc with H1/H2/H3 headings. `section_depth=1` → one file per H1,
  every `SectionEntry.level == 1`, H2 text present as `\subsection{}` inside the parent file and
  absent from `sections/` as a filename. `section_depth=2` → H2s get their own files, H3s inline
  as `\subsubsection{}`. `section_depth=4` and `0` both raise `ConversionError`.
- **Unit (naming):** `"2.1  Agent Evaluation and the Deployment Gap"` → slug
  `<NN>-agent-evaluation-and-the-deployment-gap` and `\subsection{Agent Evaluation and the
  Deployment Gap}` — no leading `2.1` in either. A heading whose text is only `"4.2"` keeps it.
- **Unit (abstract):** a doc with an `Abstract` paragraph before the first heading produces
  `sections/<NN>-abstract.tex` containing `\begin{abstract}`, a `frontmatter.tex` that no
  `\input` references, and a `main.tex` whose abstract `\input` sits before the body block.
- **Integration (real manuscript):** convert `papers/apip/manuscript/APIP_Paper_v8_tracked.docx`
  at the default depth and assert:
  - `len(list(sections_dir.glob("*.tex"))) == 10` (abstract + 9 H1s); today it is 33.
  - `{s.level for s in manifest.sections} == {1}`.
  - the file bodies contain 22 `\subsection{` commands total (23 H2s, one blank and skipped) and
    zero `\subsubsection{`.
  - no file is empty and no `SectionEntry.title` is empty.
  - slugs are unique and every `latex_path` exists on disk.
  - the titles, in `order`, are Abstract, Introduction, Background and Related Work, A Taxonomy
    of Agent Failure Modes, The APIP Framework, Formal APIP Schema, Illustrative Case Study,
    Simulation-Based Evaluation, Open Problems and Future Directions, Conclusion — the same ten
    logical sections as `papers/apip/latex/sections/`.
- **Round-trip (`main.tex` splice):** parse the generated `main.tex`; the `\input{sections/…}`
  list must have exactly 10 entries, each resolving to an existing file, in `order`, with no
  duplicates, with the abstract input before the auto-generated block and `frontmatter` absent.
- **Round-trip (compiles):** guarded by
  `@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="no TeX toolchain")` — convert
  the real manuscript with `build_pdf=True` and assert `manifest.build.status == "succeeded"` and
  that `main.pdf` exists. This is the check that the spliced `\input` list and the inlined
  `\subsection` commands are actually valid LaTeX; the current abstract handling would not have
  been caught by a structural assertion alone.
- **E2E:** `./scripts/web/start.sh`, upload the APIP manuscript, confirm the section list shows
  10 entries with subheadings nested under Background, Framework, Case Study, Simulation, and
  Open Problems; edit one section, recompile, confirm the PDF updates.
- **Edge:** a `.docx` that opens on a `Heading 2` with no preceding H1 (content lands in a
  synthetic first section, nothing dropped); a `.docx` with two identically-titled H1 headings
  (two distinct files, both `\input`, neither overwritten); a `.docx` with no headings at all
  (one section, unchanged from today); a blank heading (no file, no `\subsection{}`); a `.docx`
  with no abstract marker (no abstract file, empty marker, build still succeeds).

---

## 8. Non-Goals

- Inferring semantic filenames (`case_study.tex`) from heading text.
- Re-splitting an already-converted workspace under `documents/` in place; re-upload instead.
- Splitting on anything other than heading level — no size-based or figure-based splitting.
- Merging or reordering sections after conversion, from the UI or the API.
- Changing how figures, references, or the build pipeline work.
- Touching `papers/apip/latex/`, which is hand-edited and stays that way.
