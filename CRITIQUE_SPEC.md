## Criticism

**The converter silently discards every reference in the uploaded paper, producing a permanently broken bibliography.**

`converter.py:213–216` always writes the following — and nothing else — into `references/references.bib`, regardless of how many citations the original `.docx` contains:

```python
# Always provide a references stub
references_bib = references_dir / "references.bib"
if not references_bib.exists():
    references_bib.write_text("% TODO: Populate references extracted from the document\n")
```

All four conference templates call `\bibliography{references}` (IEEE `main.tex:69`, NeurIPS `main.tex:85`, ACM `main.tex:105`, AAAI `main.tex:91`). With an empty `.bib` file, `bibtex` produces no output and the compiled PDF has no References section — making every converted paper structurally incomplete and unsuitable for any conference submission.

The gap is invisible to users: the manifest records no warning, the UI shows no alert, and the PDF appears to build successfully (`status: "succeeded"`). Users downloading the LaTeX zip or PDF only discover the missing bibliography after the fact.

This is the single highest-impact failure because it is universal (100% of conversions), silent, and directly undermines the stated product purpose: *"turns a Word manuscript into… a conference-ready PDF."*

---

## Spec

### Goal

Extract the bibliography from the uploaded `.docx` and emit a populated `references.bib`. When extraction is partial or impossible, produce the best available output and set a visible warning in the manifest rather than silently emitting a comment stub.

### Approach

Word documents contain bibliography data in two complementary places. The extractor should try both in order:

**1. Word's built-in Sources XML** (`word/customXml/` inside the `.docx` zip)

When the author used Word's *Citations & Bibliography* feature, the document package contains a `Sources.xml` (or similar) part with structured entries: author, title, year, journal/conference, volume, pages, etc. `python-docx` exposes the raw document zip via `Document._part.package.part_related_by(...)` or by opening the `.docx` as a `zipfile.ZipFile` and scanning for `customXml/` parts containing a `<b:Sources>` root element. If found, each `<b:Source>` maps cleanly to a `@article`, `@inproceedings`, `@book`, or `@misc` BibTeX entry.

**2. Heuristic paragraph extraction**

For papers written without Word's citation manager, identify the bibliography by scanning for a heading paragraph whose text matches `References` (case-insensitive), then collect all paragraphs that follow until the next heading or end-of-document. Each collected paragraph is a raw reference string. Apply lightweight regex patterns to classify and extract fields:

- Numbered `[1]` or `1.` prefix → strip the number, treat remainder as citation text
- `Author(s), "Title," Venue, Year.` → parse author, title, venue, year heuristically
- DOI `10.XXXX/...` anywhere → include as `doi = {...}` field
- Emit `@misc{refN, note={<raw text>}}` for entries that don't parse cleanly, so the `.bib` is syntactically valid and BibTeX does not abort

**3. Manifest warning**

Add an optional `references_warning` field to `DocumentManifest` (and `BuildResult` or top-level manifest JSON). Set it when:
- No Sources XML was found **and** no reference-section paragraphs were detected → `"No references could be extracted; references.bib is empty."`
- Partial extraction → `"Extracted N references; M entries could not be parsed and are stored as @misc stubs."`

Surface this warning in the UI (WORD tab or PDF tab banner) and in the `GET /documents/{id}` response.

### Specific changes

| File | Change |
|---|---|
| `src/docbuilder/converter.py` | Replace the stub write at line 213–216 with a call to a new `extract_references(docx_path) -> tuple[str, str | None]` that returns `(bib_content, warning_or_None)`. Write the returned content to `references.bib`. Store the warning in the manifest. |
| `src/docbuilder/refextract.py` *(new)* | Implement `extract_references`. Step 1: open `.docx` as a zip, scan `customXml/` for `<b:Sources>` and convert to BibTeX. Step 2 (fallback): use `python-docx` paragraphs to find the References section and run heuristic parsing. Return `(bib_str, warning)`. |
| `src/docbuilder/models.py` | Add `references_warning: str | None = None` to `DocumentManifest`. |
| `src/docserver/schemas.py` | Expose `references_warning` in `DocumentResponse`. |
| `web/` (React) | Show a dismissible amber banner on the WORD/PDF tab when `references_warning` is non-null. |
| `tests/test_refextract.py` *(new)* | Unit tests: Sources XML path (mock a `.docx` zip containing `<b:Sources>`), heuristic path (paragraphs with numbered citations), mixed/empty cases. |

### Acceptance criteria

1. Converting a `.docx` that used Word's citation manager produces a `references.bib` with one valid BibTeX entry per source; the built PDF includes a populated References section.
2. Converting a `.docx` with a manually typed reference list produces `@misc` stubs (one per paragraph) — BibTeX does not error and the PDF renders those entries.
3. Converting a `.docx` with no detectable references sets `references_warning` in the manifest and shows a warning banner in the UI; the build does not fail.
4. Converting a `.docx` with no detectable references does **not** silently emit the `% TODO` comment (the old stub); users are explicitly informed.
5. All existing tests continue to pass; the new `test_refextract.py` covers all three branches.
