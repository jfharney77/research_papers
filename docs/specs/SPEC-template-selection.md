# Spec: Dynamic LaTeX Template Selection (Word → LaTeX web app)

**Status:** Proposed
**Scope:** Polish + dynamic template list. No template switching on existing docs, no
multi-template compare, no new template authoring (see §7).
**Branch:** implement on `devel-apip-word2l` (the working tree is currently on the empty
`main` branch — commit this spec and the implementation there).

---

## 1. Summary & Goal

The Word → LaTeX "doc workspace" stack (`src/docbuilder` converter + `src/docserver` FastAPI
+ `web/` React app) already lets a user pick a LaTeX template when uploading a `.docx`. The
selection is functional end to end, but the list of templates is **hardcoded in the
frontend** and the default (`"ieee"`) is duplicated as a magic string across several layers.

**Goal:** make the backend the single source of truth for which templates exist. Discover
**valid, buildable** templates on the server, expose them via a new `GET /templates`
endpoint (with friendly display names and descriptions), and have the UI populate its
dropdown from that endpoint. A template is only offered if it has **both** a `latex/<name>/`
directory (with `main.tex`) **and** a working `scripts/templates/<name>/build.sh`.

This removes frontend/backend drift, surfaces clear validation errors, and makes adding a
new template a pure backend/filesystem change with no frontend edit required.

---

## 2. Current Behavior (as-is)

The capability already works; this spec hardens and de-duplicates it.

| Layer | File | Behavior |
|-------|------|----------|
| Frontend dropdown | `web/src/App.tsx` | Hardcoded `TEMPLATE_CHOICES = ["ieee","acm","neurips","aaai"]`; `<select name="template" defaultValue="ieee">`. |
| Upload request | `web/src/App.tsx` → `submitUpload()` | `POST ${API_BASE}/documents?template=<id>&build_pdf=true&overwrite=<bool>`. |
| Upload endpoint | `src/docserver/main.py` → `create_document()` | Signature already accepts `template: str = "ieee"`; calls `convert_upload(...)`. |
| Storage glue | `src/docserver/storage.py` → `convert_upload()` | Forwards `template` into `ConversionOptions`. |
| Converter | `src/docbuilder/converter.py` → `convert_document()` | Validates `LATEX_ROOT/<template>` exists (raises `ConversionError` otherwise), copies it into `documents/<id>/<template>/`, builds via `_run_build()`. |
| Build | `src/docbuilder/converter.py` → `_run_build()` | Runs `SCRIPT_ROOT/<template>/build.sh <workspace>`. |
| Persistence | `manifest.json` | `DocumentManifest.template` records the choice; `rebuild_pdf()` reuses it. |
| Response | `src/docserver/schemas.py` → `DocumentResponse.template` | Template echoed in every document response and shown in the UI. |
| Config | `src/docbuilder/config.py` | `DEFAULT_TEMPLATE = "ieee"`, plus `LATEX_ROOT`, `SCRIPT_ROOT`. |
| CLI | `src/docbuilder/cli.py` | `convert --template/-t` option, default `"ieee"`, no validation. |

**Available templates today:** `latex/ieee`, `latex/acm`, `latex/neurips`, `latex/aaai`,
each with `main.tex`, `sections/`, `references.bib` and a matching `scripts/templates/<id>/build.sh`.

**Weaknesses addressed by this spec:**
1. Frontend list can drift from what is actually on disk in `latex/`.
2. `DEFAULT_TEMPLATE` is duplicated as the literal `"ieee"` in `create_document`, `App.tsx`,
   the converter fallback, and the CLI.
3. No endpoint enumerates templates; no display names/descriptions.
4. No check that a template is actually *buildable* (has a build script) before it is offered.

---

## 3. Proposed Changes

### a. Template registry — single source of truth
New module **`src/docbuilder/templates.py`**:

- `available_templates() -> list[TemplateInfo]`
  Scans `LATEX_ROOT` for subdirectories that contain a `main.tex`. For each, sets
  `buildable=True` only when `SCRIPT_ROOT/<name>/build.sh` exists. Returns the list sorted by
  id (with the default template first, or flagged via the response `default` field).
- `TEMPLATE_METADATA: dict[str, dict[str, str]]`
  Optional per-id display metadata, e.g.
  ```python
  TEMPLATE_METADATA = {
      "ieee":    {"name": "IEEE Conference", "description": "IEEEtran two-column conference format"},
      "acm":     {"name": "ACM (acmart)",    "description": "ACM acmart article format"},
      "neurips": {"name": "NeurIPS 2025",    "description": "NeurIPS 2025 single-column style"},
      "aaai":    {"name": "AAAI 2026",       "description": "AAAI 2026 author-kit format"},
  }
  ```
  Fall back to `id.upper()` for the name and `None` for the description when an id is absent.
- `is_valid_template(name: str) -> bool` and `valid_template_ids() -> list[str]`
  (the latter for building clear error messages).

This module is the only place that touches the filesystem to decide what exists. The
converter, the upload endpoint, and the CLI all consult it.

### b. Pydantic models
Add to **`src/docbuilder/models.py`** (re-exported through `src/docserver/schemas.py`):
```python
class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str | None = None
    buildable: bool = True

class TemplateListResponse(BaseModel):
    templates: list[TemplateInfo]
    default: str          # config.DEFAULT_TEMPLATE
```

### c. Backend endpoint
Add to **`src/docserver/main.py`**:
```python
@app.get("/templates", response_model=TemplateListResponse)
def get_templates():
    return TemplateListResponse(
        templates=available_templates(),
        default=DEFAULT_TEMPLATE,
    )
```

### d. Validation hardening (defense in depth)
- **`convert_document`** (`converter.py`): keep the existing existence check but route it
  through `is_valid_template`, so the `ConversionError` message lists valid choices. When
  `build_pdf=True`, fail clearly if `SCRIPT_ROOT/<template>/build.sh` is missing rather than
  letting the subprocess error out opaquely.
- **`create_document`** (`main.py`): validate `template` against the registry up front and
  return **HTTP 400** with the list of valid ids if invalid (today this only surfaces via the
  converter's `ConversionError`).
- **`cli.py convert`**: validate `--template` against `valid_template_ids()` and print the
  valid choices on error (`typer.Exit(code=1)`), matching the existing error style.

### e. Frontend
**`web/src/api.ts`** (new, small helper module):
```ts
export type TemplateInfo = { id: string; name: string; description?: string | null; buildable: boolean };
export type TemplateListResponse = { templates: TemplateInfo[]; default: string };
export async function fetchTemplates(): Promise<TemplateListResponse> { /* GET ${API_BASE}/templates */ }
```

**`web/src/App.tsx`**:
- Remove the hardcoded `TEMPLATE_CHOICES`.
- Add state: `templates: TemplateInfo[]` and `defaultTemplate: string`.
- On mount (alongside `refreshDocuments`), call `fetchTemplates()` and store the result.
- Render options from state:
  ```tsx
  <select name="template" defaultValue={defaultTemplate}>
    {templates.map((t) => (
      <option key={t.id} value={t.id} disabled={!t.buildable} title={t.description ?? undefined}>
        {t.name}{t.buildable ? "" : " (build script missing)"}
      </option>
    ))}
  </select>
  ```
- **Graceful fallback:** if `/templates` fails, fall back to a minimal `[{id:"ieee", name:"IEEE", buildable:true}]`
  and surface the existing error banner so the form still works.

---

## 4. API Contract

`GET /templates` →
```json
{
  "templates": [
    { "id": "ieee",    "name": "IEEE Conference", "description": "IEEEtran two-column conference format", "buildable": true },
    { "id": "acm",     "name": "ACM (acmart)",    "description": "ACM acmart article format",            "buildable": true },
    { "id": "neurips", "name": "NeurIPS 2025",    "description": "NeurIPS 2025 single-column style",      "buildable": true },
    { "id": "aaai",    "name": "AAAI 2026",       "description": "AAAI 2026 author-kit format",           "buildable": true }
  ],
  "default": "ieee"
}
```
The existing `POST /documents?template=<id>` contract is unchanged; only its validation
error message improves.

---

## 5. Files Affected (implementation reference)

| File | Change |
|------|--------|
| `src/docbuilder/templates.py` | **new** — registry, metadata, validation helpers |
| `src/docbuilder/models.py` | add `TemplateInfo`, `TemplateListResponse` |
| `src/docbuilder/converter.py` | route validation through registry; check build script when building |
| `src/docbuilder/cli.py` | validate `--template`, print valid choices on error |
| `src/docserver/main.py` | add `GET /templates`; validate `template` in `create_document` |
| `src/docserver/schemas.py` | re-export / expose template schemas |
| `web/src/api.ts` | **new** — `fetchTemplates()` + types |
| `web/src/App.tsx` | remove hardcoded list; fetch + render dynamic options; fallback |

---

## 6. Verification Plan

- **Unit:** `available_templates()` returns `ieee/acm/neurips/aaai`; temporarily renaming a
  `latex/<x>` dir's expected build script makes that template report `buildable=False`.
- **API:** `curl http://localhost:8000/templates` returns the contract in §4.
- **E2E:** `./scripts/web/start.sh`, open `http://localhost:5173`, confirm the dropdown is
  populated from the server (not the old hardcoded list); upload the same `.docx` under two
  different templates and confirm each workspace's `manifest.json` records the right
  `template` and produces a PDF.
- **Edge:** rename a `scripts/templates/<id>/build.sh`; confirm that template appears disabled in
  the UI and that selecting it (via direct API call) returns a clear error listing valid
  choices.

---

## 7. Non-Goals

- Switching the template of an already-converted document without re-uploading.
- Building/comparing the same paper across multiple templates side by side.
- Authoring new template directories (a new template is simply a `latex/<id>/` dir + a
  `scripts/templates/<id>/build.sh`; once added, it appears automatically via the registry).
