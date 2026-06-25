## Criticism

**`document_id` from URL path parameters is joined to the filesystem without validation, enabling path traversal that deletes the entire repository via a single `DELETE /documents/..` request.**

The server already guards against path traversal for uploaded filenames — `safe_upload_name` (`storage.py:31–36`) strips directory components and its behaviour is explicitly tested (`test_workspace.py:23–36`). The identical protection was never applied to the `document_id` segment that arrives from URL path parameters.

Every storage and pipeline function that accepts a `document_id` joins it directly to `DOCUMENTS_ROOT` with no validation:

| Function | File | How `document_id` is used |
|----------|------|--------------------------|
| `delete_document` | `storage.py:75–79` | `target = DOCUMENTS_ROOT / document_id`; `shutil.rmtree(target)` |
| `load_document` | `storage.py:39–43` | `DOCUMENTS_ROOT / document_id / "manifest.json"` |
| `zip_directory` caller | `main.py:218` | `DOCUMENTS_ROOT / document_id / manifest.template` |
| `_critique_path` | `pipeline.py:88–89` | `DOCUMENTS_ROOT / document_id / "critique.json"` |
| `critique_document` | `pipeline.py:102` | `workspace = DOCUMENTS_ROOT / document_id` |

**The critical attack vector is `DELETE /documents/..`:**

```
DELETE /documents/.. HTTP/1.1
Host: localhost:8000
```

Starlette captures `..` as the `{document_id}` path parameter (the default regex `[^/]+` matches `..`; curl and any raw HTTP client send this verbatim without normalisation). In `delete_document`:

```python
target = DOCUMENTS_ROOT / ".."          # == REPO_ROOT (the whole project)
if not target.exists():                 # parent directory always exists → True
    raise FileNotFoundError(...)
shutil.rmtree(target)                   # destroys /home/john/fable5/research_papers
```

`DOCUMENTS_ROOT` is `REPO_ROOT / "documents"` (`config.py:9`). Python's `pathlib` does not normalise `..` until `.resolve()` is called, so `DOCUMENTS_ROOT / ".."` evaluates to the repo root on disk. `target.exists()` returns `True`, and `shutil.rmtree` deletes the entire codebase in one request.

**Secondary vectors:**

- `POST /documents/../critique` — when no key is set, `_critique_path("..")` writes `critique.json` one level above `DOCUMENTS_ROOT`, overwriting arbitrary files in the repo root.
- `GET /documents/..` and `GET /documents/../sections/foo` return 404 rather than 400 because `manifest_path.exists()` saves them — but the absence of an error response from the destructive endpoints is the critical gap.

**Authentication does not reliably prevent this.** `DOCSERVER_API_KEY` is unset in all default installs (the server logs a warning and allows all requests — `auth.py:46–53`). Even when set, the key leaks into server access logs and browser history because `auth.py:38–40` accepts it as a query-string parameter (`?api_key=…`), making an authenticated but curious operator a viable threat actor.

The gap is not theoretical — `curl -X DELETE http://localhost:8000/documents/..` is a one-liner. The contrast with `safe_upload_name` makes the omission especially clear: the developer knew path traversal was a risk and fixed it for one input source but left all URL-parameter-derived document IDs unsanitised.

---

## Spec

### Goal

Reject any `document_id` that contains path-traversal components (`..`, absolute prefixes, embedded separators) at the storage boundary, so no filesystem operation can escape `DOCUMENTS_ROOT`, and legitimate identifiers continue to work unchanged.

### Approach

Add a single, focused validator that is called at every entry point where `document_id` is joined to a path. The validator is the same pattern already used for filenames (`safe_upload_name`): use `pathlib` to inspect the proposed path relative to `DOCUMENTS_ROOT` and raise if it would escape.

**Validation logic:**

```python
import re

_SAFE_ID = re.compile(r'^[A-Za-z0-9_-]+$')

def _validate_document_id(document_id: str) -> None:
    """Raise ValueError if document_id could traverse outside DOCUMENTS_ROOT."""
    if not document_id or not _SAFE_ID.match(document_id):
        raise ValueError(
            f"Invalid document_id {document_id!r}: "
            "must be non-empty and contain only letters, digits, hyphens, or underscores."
        )
```

Using a strict allowlist (`[A-Za-z0-9_-]+`) is more robust than a denylist (`..`, `/`, `\`). All existing document IDs are produced by `snake_case(docx_path.stem)` in `converter.py:55`, which already limits output to letters, digits, and underscores; the validator is therefore backward-compatible with every document that has ever been created.

**Surface the error as HTTP 400, not 500:** The API layer must catch `ValueError` from `load_document` / `delete_document` and return a 400 response, since a 404 or 500 would be misleading and would mask the traversal attempt in monitoring.

### Specific changes

| File | Change |
|---|---|
| `src/docserver/storage.py` | Add `_validate_document_id(document_id: str) -> None` (raises `ValueError` on unsafe ids). Call it as the first statement of `load_document` and `delete_document`. |
| `src/critic/pipeline.py` | Call `_validate_document_id` (imported from `docserver.storage`, or duplicated in a shared `docbuilder.utils` helper) at the top of `_critique_path` and `critique_document`. |
| `src/docserver/main.py` | In `remove_document` (line 120) and `get_document` (line 112), add `except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc))` before the `FileNotFoundError` handler. |
| `tests/test_workspace.py` | Add parametrized tests covering `..`, `../etc`, `/etc/passwd`, `nested/path`, and `%2E%2E` (percent-encoded) as `document_id` values for `DELETE /documents/{id}`, `GET /documents/{id}`, and `GET /documents/{id}/archive`; assert all return 400, not 200/404/500. Add a unit test for `_validate_document_id` covering the allowlist boundary. |

### Acceptance criteria

1. `curl -X DELETE http://localhost:8000/documents/..` returns HTTP 400 and leaves `DOCUMENTS_ROOT`'s parent directory intact.
2. `DELETE /documents/../etc`, `GET /documents//etc/passwd`, `GET /documents/%2E%2E` all return 400.
3. `DELETE /documents/nonexistent-doc` still returns 404 (legitimate "not found" case is unaffected).
4. `DELETE /documents/my_paper_2024` still deletes the document normally (snake_case IDs continue to work).
5. `_validate_document_id("my-paper")` and `_validate_document_id("doc_1")` do not raise; `_validate_document_id("..")`, `_validate_document_id("a/b")`, `_validate_document_id("")`, and `_validate_document_id("/etc")` all raise `ValueError`.
6. All existing tests continue to pass; the new test file covers both the unit validator and the API endpoints.
