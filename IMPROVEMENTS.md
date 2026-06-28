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

## Non-blocking upload handlers (CRITIQUE_SPEC_2.md)

**Problem:** Two `async def` route handlers in `src/docserver/main.py` performed
blocking work directly on the asyncio event loop. `create_document` (LaTeX build
via `subprocess.run`, 30–120 s) and `critique_adhoc_upload` (synchronous LLM
call, 10–60 s) froze the whole server for every other request while they ran —
health checks, document listing, section edits and PDF downloads all queued up.
FastAPI only offloads `def` handlers to its anyio thread pool; `async def`
handlers run on the loop thread with no offload.

**Fix:**
- **`src/docserver/main.py:91`** — `critique_adhoc_upload` changed from
  `async def` to `def`; `data = await file.read()` replaced with the synchronous
  `data = file.file.read()` (same `SpooledTemporaryFile` pattern as
  `storage.save_upload`).
- **`src/docserver/main.py:164`** — `create_document` changed from `async def`
  to `def` (it never used `await`).

Both now match the already-correct `recompile_document` / `run_critique`
handlers and are dispatched to the thread pool, keeping the event loop free.

- **`tests/test_concurrency.py`** *(new)* — asserts both handlers are sync
  `def`; verifies `GET /health` returns 200 in <1 s while a 2 s blocking
  `POST /documents` is in flight; verifies two simultaneous uploads run
  concurrently (~1 s, not serialized ~2 s); and confirms `UploadFile.file.read()`
  round-trips bytes identically. Tests drive the ASGI app via
  `httpx.AsyncClient` + `anyio` task groups (run through `anyio.run` since no
  async-pytest plugin is configured).

**Note:** the test suite could not be executed in this session — every Python /
pytest invocation was blocked by the permission gate. Run
`uv run --group dev pytest` to verify.
