## Criticism

**Two `async def` API handlers perform blocking work directly in the asyncio event loop, making the server completely unresponsive during every upload conversion and every ad-hoc critique.**

`src/docserver/main.py` has exactly two `async def` route handlers among the eighteen total:

| Line | Handler | Why `async`? | What it actually does |
|------|---------|--------------|----------------------|
| 91 | `critique_adhoc_upload` | `await file.read()` | Calls synchronous `critique_adhoc()` → blocking LLM HTTP request (10–60 s) |
| 164 | `create_document` | `await` not used at all | Calls synchronous `convert_upload()` → blocking `subprocess.run()` LaTeX build (30–120 s) |

The problem is FastAPI's contract: a route declared `async def` runs directly **on the event loop thread** with no thread-pool offload. A route declared `def` is automatically dispatched to FastAPI's default `anyio` thread pool executor, letting other requests proceed concurrently.

The repo demonstrates the correct pattern right next door: `def recompile_document` (line 188) and `def run_critique` (line 75) are regular `def`, so they are handled in the thread pool even though they do the same kinds of blocking work (LaTeX subprocess and LLM call). The two `async def` endpoints break that pattern.

**`create_document` does not even use `await`**: `convert_upload` reads the file via the synchronous `upload.file.read()` inside `save_upload`, so the only reason for the `async` declaration was cargo-culted from the UploadFile FastAPI pattern, and it was never needed.

**`critique_adhoc_upload`** does use `await file.read()`, but immediately hands the bytes to the synchronous `critique_adhoc()` which calls either:
- `anthropic.Anthropic().messages.parse(...)` — synchronous Anthropic SDK
- `httpx.post(...)` — synchronous httpx (`src/critic/providers/ollama.py:35`)

Both block the calling thread — but that calling thread is the event loop when the handler is `async def`.

**Concrete impact:**
- During a LaTeX build (30–120 s), all other requests — health checks, `GET /documents`, section edits, PDF downloads — queue up with no response.
- During a critique API call (10–60 s), the same total freeze occurs.
- Under any concurrent load the server appears hung. A single malicious upload (or slow Ollama model) can hold the server hostage for the full build timeout window (default 300 s per `LATEX_BUILD_TIMEOUT`).

The test suite passes because `TestClient` is single-threaded and does not exercise concurrent request handling.

---

## Spec

### Goal

Restore the thread-pool dispatch that FastAPI provides automatically for `def` handlers, so that LaTeX builds and LLM calls never block the event loop and the server remains responsive under concurrent load.

### Approach

The fix is minimal and local: change the two async handlers to synchronous `def`. FastAPI will then dispatch each to the thread pool executor, matching the already-correct behavior of `recompile_document` and `run_critique`.

For `critique_adhoc_upload`, the one real async operation (`await file.read()`) must be replaced with the synchronous equivalent (`file.file.read()`), which is identical to the pattern used in `save_upload` on line 49 of `storage.py`. This is safe because `UploadFile.file` exposes the underlying `SpooledTemporaryFile`, which is already fully buffered in memory or on disk by the time the handler executes.

No changes to the critique pipeline, the LaTeX sandbox, or the storage layer are required.

### Specific changes

| File | Change |
|---|---|
| `src/docserver/main.py:91` | Change `async def critique_adhoc_upload` → `def critique_adhoc_upload`. Replace `data = await file.read()` with `data = file.file.read()`. |
| `src/docserver/main.py:164` | Change `async def create_document` → `def create_document`. No other change needed (no `await` was used). |

**Before (`main.py:91`):**
```python
@app.post("/critic/adhoc", response_model=CritiqueResult)
async def critique_adhoc_upload(file: UploadFile = File(...)):
    name = file.filename or ""
    if not (name.endswith(".pdf") or name.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only .pdf and .docx uploads are supported")
    data = await file.read()
    ...
```

**After:**
```python
@app.post("/critic/adhoc", response_model=CritiqueResult)
def critique_adhoc_upload(file: UploadFile = File(...)):
    name = file.filename or ""
    if not (name.endswith(".pdf") or name.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only .pdf and .docx uploads are supported")
    data = file.file.read()
    ...
```

**Before (`main.py:164`):**
```python
@app.post("/documents", response_model=CreateDocumentResponse)
async def create_document(
    file: UploadFile = File(...),
    ...
):
```

**After:**
```python
@app.post("/documents", response_model=CreateDocumentResponse)
def create_document(
    file: UploadFile = File(...),
    ...
):
```

### Acceptance criteria

1. Both handlers are declared `def` (not `async def`) and the existing tests continue to pass.
2. A new concurrency test spawns two simultaneous `POST /documents` requests against a minimal `.docx`; both complete without either blocking the other beyond the build-time bound. (Use `httpx.AsyncClient` with `anyio.create_task_group` or `asyncio.gather`.)
3. A new concurrency test hits `GET /health` while a `POST /documents` is in flight and receives a `200` response within 1 second, confirming the event loop is not frozen.
4. `file.file.read()` in the adhoc handler returns the same bytes as `await file.read()` did; a test verifying round-trip byte identity with a known fixture file confirms correctness.
5. No changes to the sandbox, storage, or critic pipeline are needed; the diff is two one-word substitutions and one method-call change.
