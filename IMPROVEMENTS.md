# Improvements

## Bibliography extraction (CRITIQUE_SPEC.md)

**Problem:** The converter silently discarded every reference. It wrote a
`% TODO` comment stub into `references/references.bib` (a subdirectory that
`\bibliography{references}` never even reads), so every converted paper compiled
with the template's placeholder bibliography — or none at all — with no warning
anywhere.

**Changes:**

- **`src/docbuilder/refextract.py`** *(new)* — `extract_references(docx_path) ->
  (bib_content, warning)`. Tries Word's built-in *Citations & Bibliography*
  Sources XML first (scans `customXml/*.xml` for a `<b:Sources>` root and maps
  each `<b:Source>` to `@article`/`@inproceedings`/`@book`/etc.). Falls back to
  heuristic paragraph extraction: finds the `References`/`Bibliography` heading,
  collects following paragraphs until the next heading, strips `[1]`/`1.`
  numbering, parses `Author, "Title," Venue, Year` plus any DOI, and emits valid
  `@misc` stubs for lines that don't parse so BibTeX never aborts.
- **`src/docbuilder/converter.py`** — replaced the stub write with a call to
  `extract_references`. The extracted bib is written to the template-root
  `references.bib` (the file LaTeX actually reads, replacing the placeholder) and
  mirrored under `references/`. The returned warning is stored on the manifest.
- **`src/docbuilder/models.py`** — added `references_warning: str | None` to
  `DocumentManifest`.
- **`src/docserver/schemas.py`** — exposed `references_warning` on
  `DocumentResponse` (surfaced by `GET /documents` and `GET /documents/{id}`).
- **`web/src/App.tsx` / `App.css`** — dismissible amber banner on the PDF/WORD
  tabs when `references_warning` is set.
- **`tests/test_refextract.py`** *(new)* — covers the Sources-XML path, the
  heuristic numbered-reference path, unparseable `@misc` stubs (with warning),
  the section-stops-at-next-heading boundary, and the empty/no-references case
  (warning set, no `% TODO` stub emitted).

**Note:** the test suite could not be executed in this session because Python
execution was blocked by the sandbox permission gate. Run
`uv run --group dev pytest` to verify.
