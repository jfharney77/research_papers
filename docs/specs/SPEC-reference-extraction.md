# Spec: Reference Extraction from `.docx` (bibliography → BibTeX)

**Status:** Proposed
**Scope:** Reference-section detection and reference-line parsing in
`src/docbuilder/refextract.py`, plus the two places the result is consumed
(`src/docbuilder/converter.py`, the `references_warning` banner in `web/src/App.tsx`).
No citation rewriting in the body text, no network lookups (see §8).
**Branch:** implement on `devel-reorg`.

---

## 1. Summary & Goal

`extract_references(docx_path) -> (bib_content, warning)` is supposed to turn the
bibliography of an uploaded `.docx` into a populated `references.bib`. On the project's own
manuscript it produces nothing at all.

```
$ papers/apip/manuscript/APIP_Paper_v8_tracked.docx
('% No references could be extracted from the source document.\n',
 'No references could be extracted; references.bib is empty.')
```

That document has 31 clean numbered reference entries in it (paragraphs 190–220), and the
hand-written `papers/apip/latex/references.bib` maintained for the same paper has 35 entries.

**Goal:** extract the reference list from a manuscript whose author formatted the
"References" heading by hand instead of applying a Word Heading style, and parse the
`[n] Author. (Year). Title. Venue.` shape that dominates real manuscripts into typed BibTeX
entries rather than untyped `@misc` stubs.

---

## 2. Current Behavior (as-is)

`extract_references` runs a three-step strategy:

1. **Word Sources XML** (`_read_sources_xml`) — reads `customXml/*.xml` looking for a
   `<b:Sources>` root. Only populated when the author used Word's *Citations & Bibliography*
   feature.
2. **Heuristic paragraph extraction** (`_read_reference_paragraphs`) — finds the References
   heading and collects following paragraphs.
3. **Per-line parsing** (`_heuristic_to_bibtex`) — regex-parses each collected line, falling
   back to a raw-text `@misc` stub.

Both failure modes fire on the real manuscript.

### a. The reference section is never found

`_read_reference_paragraphs` (refextract.py:183) gates on the paragraph style:

```python
is_heading = style_name.startswith("Heading") or style_name == "Title"
...
if is_heading and _is_references_heading(text):
    in_references = True
```

In `APIP_Paper_v8_tracked.docx`, paragraph 189 is exactly the text `References` but its style
is **`Normal`** — the author made it a heading by bolding the run and setting it to 12pt
(`bold=True`, `font.size=152400` EMU) rather than applying *Heading 1*. `in_references` never
becomes `True`, the loop collects nothing, and `extract_references` returns the empty-bib
warning.

This is not a document that lacks structure elsewhere: the same file uses real Heading styles
throughout (`Counter({'Normal': 188, 'Heading 2': 23, 'Heading 1': 9, 'List Paragraph': 6})`).
Only `Abstract` (para 7) and `References` (para 189) are hand-formatted — which is the common
pattern, because those two are usually typed before the author settles on a style scheme.

Step 1 cannot rescue it: the package has 15 parts and **no `customXml/` entry at all**, so
`_read_sources_xml` returns `[]`.

### b. Even when found, the lines do not parse

`_heuristic_to_bibtex` recognizes exactly one shape: a title in straight or curly quotes
(`_QUOTED_TITLE_RE`). Feeding it the 31 real reference paragraphs directly:

```
31 entries -> parsed cleanly: 1 of 31
```

The single "success" is a false positive: entry [21] contains `Team membership change
“events”: A review and reconceptualization`, so the quoted word `events` is captured as the
title and the rest of the citation is shredded into `author`/`howpublished`. The other 30 are
APA-style and quote nothing:

```
[1] Anthropic. (2023). Constitutional AI: Harmlessness from AI feedback. arXiv preprint arXiv:2212.08073.
[16] Morgeson, F.P., Mitchell, T.R., & Liu, D. (2015). Event system theory: An event-oriented approach
     to the organizational sciences. Academy of Management Review, 40(4), 515–537.
[22] Wegner, D.M. (1987). Transactive memory: A contemporary analysis of the group mind.
     In B. Mullen & G.R. Goethals (Eds.), Theories of Group Behavior (pp. 185–208). Springer.
```

So fixing only §2a would replace "zero references" with "31 untyped stubs plus a warning".

### c. Downstream consequences

- **Empty bib breaks the build.** With no `@` entries, bibtex emits
  `\begin{thebibliography}{}` with no `\bibitem`, and pdflatex fails with
  "Something's wrong--perhaps a missing \item". `_rewrite_main` (converter.py:326) now
  comments out `\bibliographystyle`/`\bibliography` when `has_references` is false. The result
  is visible in the committed output at `papers/apip/latex.imported/main.tex:67`:
  ```
  % [no references extracted] \bibliographystyle{IEEEtran}
  % [no references extracted] \bibliography{references}
  ```
  **That patch stays.** It is a safety net for genuinely reference-free manuscripts; it is not
  the fix for this bug, and it should stop triggering on documents like this one.
- **The reference list leaks into the body.** `_build_from_docx` treats every non-heading
  paragraph with text as prose for the current section. Because nothing tells it where the
  bibliography starts, all 31 reference lines are appended to the last section — see
  `papers/apip/latex.imported/sections/9-conclusion.tex`, which ends with the raw reference
  list as running text.
- **Nothing cites the entries.** No template's `main.tex` contains `\nocite`, and the
  converter emits body citations as literal `[1]` text, not `\cite{...}`. So even a correctly
  populated `references.bib` prints an empty bibliography today.

---

## 3. Design

### a. One shared detector for the reference span

New function in `refextract.py`:

```python
def find_reference_span(paragraphs: list[Paragraph]) -> tuple[int, int] | None:
    """Return (start, end) paragraph indices of the reference list body, or None."""
```

`start` is the index of the first reference paragraph (the one *after* the label, when a
label exists); `end` is exclusive. `_read_reference_paragraphs` becomes a thin wrapper that
calls this and returns the joined entry strings. The converter imports the same function so
the body and the bibliography agree on where the references begin (§3e).

### b. Locating the heading without Word Heading styles

Replace the `style_name.startswith("Heading")` gate with a scored predicate,
`_looks_like_heading(paragraph) -> bool`, that accepts a paragraph as a heading when its text
is short (< 60 chars, no terminal period) **and** any of:

1. style is `Heading*` or `Title` (today's rule, kept);
2. every non-empty run has `bold=True` (the case in this document);
3. the text is all upper-case letters (`REFERENCES`);
4. every non-empty run carries an explicit `font.size` larger than the document's default
   body size (body runs in this document inherit, i.e. `font.size is None`; the heading runs
   are an explicit 12pt).

`_is_references_heading` already normalizes the label and covers `references`, `bibliography`,
`referencescited`, `workscited`. Extend it with `reference` (singular) and `literaturecited`,
and strip any leading section number (`7. References`, `VII. REFERENCES`) before normalizing.

Scan for the **last** matching label in the document, not the first. Manuscripts contain
"References" in a table of contents, in a cross-reference sentence, and occasionally as a
subsection of related work; the real list is the final one. Only accept a candidate if at
least one non-empty paragraph follows it.

### c. Fallback anchor: a run of numbered entries

If no label is found, look for the bibliography by its shape. Walk the paragraphs and find
maximal runs of consecutive non-empty paragraphs matching `_NUMBER_PREFIX_RE`
(`[1]` / `1.` / `1)`), where the captured numbers ascend by one and the run starts at 1 or 2.
Accept the run when it has **at least 5 entries** and begins in the last 40% of the document.
`start` is the run's first paragraph. This handles manuscripts where the label was deleted,
sits inside a text box, or is an image.

Author–year lists (`Bauer, T.N., Erdogan, B. (2025). …`) have no numbering and are not covered
by this fallback; they still require the label. That is acceptable — the label is present in
practically every such document.

### d. Where the list ends

Collect forward from `start` until any of:

1. `_looks_like_heading()` is true for a paragraph whose text is *not* a reference (e.g.
   `Appendix A`, `Acknowledgments`) — the existing break condition, now using the widened
   heading test;
2. a paragraph starts a new numbered sequence that resets to 1 (a following numbered list);
3. three or more consecutive empty paragraphs (the document tail — this file ends with five
   empty paragraphs at 221–225);
4. end of document.

**Continuation lines.** Inside a numbered list, a non-empty paragraph with *no* number prefix
is appended to the previous entry with a single space rather than starting a new one. Word
wraps long citations into separate paragraphs often enough that treating each as its own
reference produces garbage entries. When the list is *not* numbered (label-anchored,
author–year style), every non-empty paragraph is its own entry, as today.

Reject the whole span if it yields fewer than 2 entries, or if the mean entry length is under
20 characters — cheap guards against latching onto a stray bold word.

### e. Keeping references out of the body

`_build_from_docx` (converter.py:126) calls `find_reference_span` once, before its paragraph
loop, and skips indices `>= start_of_label` (the label paragraph itself, plus everything
through `end`). This removes the duplicated reference list from
`sections/9-conclusion.tex`-style output. When the span is `None`, behavior is unchanged.

### f. Parsing the APA shape

Split `_heuristic_to_bibtex` into a detector-per-shape pipeline. Keep the existing quoted-title
branch, but run it **after** the structured parse and only when the quotes wrap something that
plausibly is a title (≥ 3 words) — this kills the `“events”` false positive on entry [21].

New `_parse_apa(text) -> dict[str, str] | None` for
`Authors. (Year). Title. Venue[, volume(issue), pages].`:

- **year** — first `(19xx|20xx)` in parentheses. Its position splits authors from the rest.
- **author** — everything before the year parenthesis, trailing period stripped. Normalize
  `A, B, & C` and `et al.` into BibTeX `and` separation; `et al.` becomes a literal
  `and others`. Corporate authors with no comma (`Anthropic`, `European Parliament and
  Council`) are brace-protected: `{Anthropic}`.
- **title** — the first sentence after the year, ending at `. ` that is not inside a known
  abbreviation (`et al.`, initials like `D.L.`, `pp.`, `Eds.`, `arXiv:`). Colons inside the
  title are preserved.
- **venue and the rest** — the remainder, mined for:
  - `arXiv:NNNN.NNNNN` / `arXiv preprint …` → `eprint` + `archivePrefix = {arXiv}`,
  - `doi:10.…` or a bare DOI (`_DOI_RE`, already present) → `doi`,
  - `Volume(Issue), start–end` → `volume`, `number`, `pages` (en-dash normalized to `--`),
  - `pp. 185–208` → `pages`,
  - `In <editors> (Eds.), <book title>` → `booktitle` + `editor`,
  - `Proceedings of …` / `In Proc. …` → `booktitle`,
  - a trailing `Publisher.` with no volume/pages → `publisher`.

**Entry type** is chosen from what was found, in order: `booktitle` from an `(Eds.)` or
`In …` construction → `@incollection`; `booktitle` from `Proceedings` → `@inproceedings`;
`volume`/`number`/`pages` with a journal-looking venue → `@article`; `publisher` only →
`@book`; arXiv or URL only → `@misc`. Everything else → `@misc`.

**Cite keys.** Today every entry is `ref<N>`. Switch to `<lastname><year><firsttitleword>`
(lowercased, ASCII-folded, non-alphanumerics dropped), matching the hand-written
`papers/apip/latex/references.bib` convention (`anthropic2023constitutional`,
`bauer2025newcomer`). Deduplicate with `a`/`b` suffixes. Fall back to `ref<N>` when no author
or year could be parsed. Emit `% [n]` as a comment above each entry so a human can map the
BibTeX back to the numbering in the Word file.

Keep the current behavior of retaining the raw line in a `note = {...}` field — nothing is
lost when the parse is imperfect, and `_escape_braces` still applies.

### g. Partial parses and stubs

The `@misc` stub path stays as the last resort, unchanged in form: a valid entry carrying only
`note = {<raw line>}`. What changes is the reporting granularity. `extract_references` returns
a small result object (or keeps the tuple and adds counts to the warning string — either is
fine, but the counts must reach the manifest):

- `total` — entries found in the span,
- `typed` — entries that got a type other than `@misc`,
- `stubs` — entries that fell through to the raw-note stub.

### h. `references_warning`

`DocumentManifest.references_warning` (models.py:55) is surfaced as a dismissible banner in
`web/src/App.tsx:514`. Today it says one of two things: nothing, or "N entries could not be
parsed". Make it report the source and the shape of the result, since "31 references, 4 not
fully parsed" is a very different message from "no references found":

| Situation | Warning |
|-----------|---------|
| Sources XML used | `None` |
| Label found, all entries typed | `None` |
| Span found, some stubs | `Extracted 31 references; 4 entries could not be fully parsed and are stored as @misc stubs.` |
| Span found only via the numbered-run fallback | prefix the above with `No "References" heading was found; the list was detected from its numbering.` |
| Nothing found | `No references could be extracted; references.bib is empty and the \bibliography command has been commented out in main.tex.` (say what happened to the build, since that is the user-visible effect) |

The empty case keeps writing the comment-only bib and keeps `has_references=False`, so
`_rewrite_main` keeps commenting out the bibliography.

### i. `\nocite{*}`

Extracted entries are never cited, so bibtex prints an empty bibliography even with a full
`references.bib`. When `has_references` is true, `_rewrite_main` inserts `\nocite{*}`
immediately before the `\bibliography{...}` line so every extracted entry appears in the PDF.
Mapping the manuscript's inline `[n]` markers to real `\cite{}` commands is out of scope (§8).

---

## 4. Files Affected

| File | Change |
|------|--------|
| `src/docbuilder/refextract.py` | `find_reference_span`, `_looks_like_heading`, numbered-run fallback, continuation joining, `_parse_apa` + entry typing, cite keys, richer warning |
| `src/docbuilder/converter.py` | `_build_from_docx` skips the reference span; `_rewrite_main` adds `\nocite{*}` when entries exist (the comment-out path is unchanged) |
| `src/docbuilder/models.py` | optional counts alongside `references_warning` if the result object lands in the manifest |
| `web/src/App.tsx` | no logic change; the banner renders whatever string arrives |
| `tests/test_refextract.py` | new cases, §6 |

---

## 5. Behavior on the reference document

After the change, `extract_references(papers/apip/manuscript/APIP_Paper_v8_tracked.docx)`
must return 31 entries, no fewer than 25 of them typed (`@article`/`@inproceedings`/
`@incollection`/`@book`), with `anthropic`, `bauer`, `kirkpatrick`, `wegner`, and `kolt` all
present as authors, and `10.1145/3630106.3658948` captured as a DOI on entry [26]. The
converted `sections/*.tex` must no longer contain `Kirkpatrick, D.L. (1994)`.

---

## 6. Testing

**The current 88-test suite passes with this bug wide open** (`uv run --group dev pytest` →
`88 passed`). `tests/test_refextract.py` builds every fixture with `doc.add_heading(...)`,
which applies the real `Heading 1` style, and every reference line it feeds in has a quoted
title. Both assumptions are exactly the ones the real manuscript violates, so the suite tests
the two code paths that work and none of the ones that fail. Fixtures must be built the way
authors actually write.

New unit fixtures, built with `python-docx` in `tmp_path`:

- Bold `Normal` "References" paragraph followed by numbered entries → 3 entries extracted.
- All-caps `REFERENCES` with no bold → extracted.
- `7. References` (numbered label) → extracted.
- Larger-font `Normal` label with body runs at default size → extracted.
- No label at all, 6 ascending `[n]` paragraphs in the last third of the document → extracted
  via the fallback, warning mentions the missing heading.
- A `References` mention in a TOC near the top plus a real list at the end → the last one wins.
- A numbered entry wrapped across two paragraphs → one entry, not two.
- `Appendix A` heading (bold `Normal`) after the list → the appendix text is excluded.
- Five trailing empty paragraphs → not counted as entries.

Parsing cases, asserted on the string output:

- `[1] Anthropic. (2023). Constitutional AI: … arXiv preprint arXiv:2212.08073.` → `@misc`,
  `author = {{Anthropic}}`, `year = {2023}`, eprint captured.
- `[16] Morgeson, F.P., … (2015). Event system theory: … Academy of Management Review, 40(4), 515–537.`
  → `@article` with `volume = {40}`, `number = {4}`, `pages = {515--537}`.
- `[22] Wegner, D.M. (1987). … In B. Mullen & G.R. Goethals (Eds.), Theories of Group Behavior (pp. 185–208). Springer.`
  → `@incollection` with `booktitle`, `editor`, `pages`, `publisher`.
- `[21] … Team membership change “events”: A review …` → the quoted word is **not** taken as
  the title (regression guard for the current false positive).
- `[26] … doi:10.1145/3630106.3658948` → `doi` field.
- An unstructured line → `@misc` stub with `note`, counted in `stubs`.
- Existing Sources-XML and empty-document tests must still pass unchanged.

**E2E:** upload `papers/apip/manuscript/APIP_Paper_v8_tracked.docx` through the running app
(`./scripts/web/start.sh`), confirm `documents/<id>/ieee/references.bib` holds ~31 entries,
that `main.tex` contains live (not commented) `\bibliographystyle`/`\bibliography` lines plus
`\nocite{*}`, that the built PDF ends with a printed reference list, that no section `.tex`
contains reference-list text, and that no warning banner appears — or a "4 could not be
parsed" one does, which is fine.

**Edge:** a `.docx` with no bibliography at all still returns the empty-bib warning, still
writes the comment-only `references.bib`, and still compiles because `_rewrite_main` comments
the bibliography out. A `.docx` with Word Sources XML still takes step 1 and never reaches
the heuristics. A corrupt/unreadable `.docx` still returns `[]` from the paragraph reader
rather than raising.

**Regression:** re-run the 4 committed template builds (`scripts/templates/*/build.sh`) with a
populated `references.bib` to confirm each `.bst` accepts the generated entry types —
`@incollection` under `IEEEtran`, `abbrvnat`, `ACM-Reference-Format`, and `aaai2026.bst`.

---

## 7. Risks

- Widening heading detection to "any short bold line" risks starting the span on a bold
  in-body label. The `_is_references_heading` label check, the last-match rule, and the
  minimum-entry-count guard all constrain it; the fallback anchor additionally requires
  ascending numbering.
- The APA parser is regex-driven and will mis-slice unusual citations. The `note` field keeps
  the raw text on every entry, so a bad parse is recoverable by hand and never loses data.
- `\nocite{*}` prints every extracted entry whether or not the text cites it. That is the
  intended behavior here: the entries came from the author's own reference list.

---

## 8. Non-Goals

- Rewriting inline `[1]` markers in the body into `\cite{...}` keys.
- Any network lookup (Crossref, arXiv, Semantic Scholar) to enrich or verify entries.
- Author-name normalization beyond splitting on `,`/`&`/`and` — no first-name expansion, no
  disambiguation of two authors sharing a surname.
- Non-Latin or non-English reference lists.
- References stored in tables, footnotes, endnotes, or text boxes (`document.paragraphs` does
  not reach them).
- A UI for editing extracted references; `references.bib` remains hand-editable on disk and
  through the existing section-editing flow.
