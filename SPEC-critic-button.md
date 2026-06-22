# Spec: "Critic" Button (per-section criticism + AI-genericness analysis)

**Status:** Proposed
**Branch:** implement on `devel-apip-word2l`
**Decisions baked in (from the user):** configurable **multi-provider** LLM backend (Claude / Ollama / Cerebras); input is **both** existing converted documents **and** ad-hoc PDF/Word upload; AI-genericness score is **hybrid** (deterministic heuristics + LLM).

---

## 1. Summary & Goal

Add a **Critic** action to the Word → LaTeX web app. Given a paper — either a document already in the workspace or an ad-hoc uploaded PDF/`.docx` — the Critic analyzes it **section by section** and returns, per section:

1. **3 criticisms** (substance/clarity/structure), each with a concrete suggestion.
2. An **"AI-genericness" score** (0–100) measuring how much the prose reads like generic LLM output, computed as a **hybrid** of deterministic text heuristics and an LLM judgment.
3. **De-AI tips** — concrete rewrite guidance to make sentence structures less "AI-like," grounded in the specific signals detected in that section.

Plus a **document-level roll-up** (mean AI score, recurring issues).

The LLM is accessed through a **provider abstraction** so the backend can run against Claude (Anthropic SDK), a local Ollama model, or Cerebras, selected by config.

---

## 2. Where it fits the existing app

- Documents already expose per-section LaTeX at `documents/<id>/<template>/sections/<slug>.tex`, listed in `manifest.json` (`DocumentManifest.sections`). The Critic reuses this — no re-parsing of the PDF needed for in-workspace docs.
- The doc server (`src/docserver/`) gains new endpoints; the React app (`web/`) gains a **Critic** tab/button next to the existing PDF / LaTeX / Word / Log tabs (see `web/src/App.tsx`).
- Ad-hoc uploads reuse `python-docx` (already a dependency) for `.docx`; PDFs need a text extractor (new dep, §6).

---

## 3. Analysis pipeline (per section)

```
section text
   │  (strip LaTeX → plain prose; for PDF/docx, extract prose directly)
   ▼
┌─ heuristics (deterministic) ─────────────┐     ┌─ LLM (provider) ───────────────┐
│ stock-phrase hits, sentence-length        │ ──▶ │ given prose + heuristic signals: │
│ burstiness, lexical diversity, transition │     │  • 3 criticisms (+ suggestions)  │
│ density, tricolon/"rule of three" rate    │     │  • ai_score_model (0–100)        │
│  → ai_score_heuristic (0–100) + signals[] │     │  • deai_tips[] referencing signals│
└───────────────────────────────────────────┘     └──────────────────────────────────┘
                       │                                          │
                       └────────────── combine ───────────────────┘
                          ai_score = round(0.5*heuristic + 0.5*model)
```

### 3a. Deterministic heuristics — `src/critic/heuristics.py` (new)
Pure-Python, no network, fully unit-testable. Operates on plain prose. Computes sub-signals, each mapped to 0–100 and averaged into `ai_score_heuristic`, and emits human-readable `signals` strings used both in the UI and as LLM context:

- **Stock/filler phrases** — count matches against a curated list (`delve`, `moreover`, `furthermore`, `it is important to note`, `plays a crucial role`, `rich tapestry`, `navigating the landscape`, `underscores the importance`, `leverage`, `robust`, `seamless`, `comprehensive`, `in the realm of`, `it is worth noting`, …). Normalize per 1000 words.
- **Burstiness** — low standard deviation of sentence length → AI-like. Humans vary sentence length more.
- **Lexical diversity** — type/token ratio; very high uniformity of openings (e.g. many sentences starting with "This"/"These"/"Moreover").
- **Transition density** — share of sentences opening with a transition word.
- **Tricolon rate** — frequency of "X, Y, and Z" triples (LLMs overuse the rule of three).
- **Em-dash / hedge density** — `—` per 1000 words, hedges ("arguably", "notably", "significantly").

Returns `HeuristicReport(ai_score_heuristic: int, signals: list[str])`, e.g. `["12 filler phrases / 1k words", "low sentence-length variance (σ=3.1)", "5 'rule-of-three' constructions"]`.

### 3b. LLM judgment — via the provider (§4)
One structured-output call per section. System prompt = a fixed **critic rubric** (cacheable). User prompt = the section prose + the heuristic `signals`. The model returns JSON conforming to the schema in §5. Asking for exactly 3 criticisms and grounding the de-AI tips in the supplied signals keeps output focused and reproducible.

### 3c. LaTeX stripping — `src/critic/textprep.py` (new)
`strip_latex(tex) -> str`: remove preamble/commands (`\section{}`, `\cite{}`, `\input{}`, math, comments) leaving readable prose for both heuristics and the LLM. For PDF/`.docx` ad-hoc input, extract prose directly (no stripping).

---

## 4. Provider abstraction (multi-provider) — `src/critic/providers/`

```python
class CritiqueProvider(Protocol):
    name: str
    def analyze_section(self, *, rubric: str, prose: str, signals: list[str]) -> SectionLLMResult: ...
```

`get_provider()` reads config and returns one of:

| Provider | Module | Notes |
|---|---|---|
| **Claude** | `providers/claude.py` | Official `anthropic` SDK. Model **`claude-opus-4-8`**, `thinking={"type":"adaptive"}`, structured output via `messages.parse(output_format=PydanticModel)` (or `output_config={"format":{"type":"json_schema","schema":…}}`). Cache the rubric system block (`cache_control: ephemeral`). `max_tokens≈4000` (non-streaming is fine at this size). Handle `stop_reason=="refusal"`. |
| **Ollama** | `providers/ollama.py` | Local model on the Windows host (reach via the WSL gateway IP, not `localhost` — see [[ollama-windows-host-wsl]]). `POST /api/chat` with `format` set to the JSON schema; model from config (e.g. `qwen2.5`). |
| **Cerebras** | `providers/cerebras.py` | `gpt-oss-120b` via the Cerebras OpenAI-compatible endpoint; JSON mode / schema. API key from env. |

**Selection (env):** `CRITIC_PROVIDER=claude|ollama|cerebras` (+ provider-specific: `ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`/`CRITIC_OLLAMA_MODEL`, `CEREBRAS_API_KEY`/`CRITIC_CEREBRAS_MODEL`). Every provider returns the **same** `SectionLLMResult`, so the pipeline and the API are provider-agnostic. The Protocol makes providers trivially **mockable** in tests (no network).

Dependencies are optional/lazy-imported so the app runs even if only one provider's SDK is installed.

---

## 5. Data model — `src/critic/models.py` (new), re-exported via docserver schemas

```python
class Criticism(BaseModel):
    category: Literal["substance", "clarity", "structure", "rigor", "style"]
    issue: str
    suggestion: str

class SectionCritique(BaseModel):
    section_slug: str
    title: str
    criticisms: list[Criticism]            # exactly 3
    ai_score: int                          # 0–100 combined
    ai_score_breakdown: dict               # {"heuristic": int, "model": int}
    ai_signals: list[str]                  # detected patterns
    deai_tips: list[str]                   # 2–4 concrete rewrite tips

class CritiqueResult(BaseModel):
    document_id: str | None                # None for ad-hoc
    provider: str
    created_at: datetime
    overall_ai_score: int                  # mean of section scores
    summary: str                           # recurring issues across sections
    sections: list[SectionCritique]
```

`SectionLLMResult` is the LLM-only slice (criticisms + model score + tips); the pipeline merges it with the heuristic score to build `SectionCritique`.

---

## 6. Backend endpoints — `src/docserver/main.py`

| Method & path | Purpose |
|---|---|
| `GET /critic/providers` | Report available providers + the active one (UI shows which backend is in use). |
| `POST /documents/{id}/critique` | Run the Critic on an existing workspace doc (uses its section files). Persists `documents/<id>/critique.json` and returns `CritiqueResult`. |
| `GET /documents/{id}/critique` | Return the cached `critique.json` if present (avoid re-running/re-paying). |
| `POST /critic/adhoc` | Multipart upload of a standalone `.pdf` or `.docx`; extract → split into sections (by headings; fall back to one "Document" section) → run pipeline → return `CritiqueResult` (not persisted to a workspace). |

Caching: `POST /documents/{id}/critique` writes a sidecar so re-opening the tab is instant; add `?refresh=true` to force a re-run. Long runs (many sections × LLM latency) should stream progress or run section calls concurrently; document a soft cap (e.g. 30 sections) and surface partial failures per section rather than failing the whole document.

**New dependency:** `pypdf` (or `pdfplumber`) for PDF text extraction, added to `pyproject.toml`. `python-docx` (already present) handles `.docx`.

---

## 7. Frontend — `web/src/App.tsx` (+ `web/src/api.ts`)

- **Existing docs:** add a **Critic** tab alongside `pdf/latex/word/log`. On open, `GET /documents/{id}/critique`; if absent, show a "Run Critic" button → `POST …/critique` with a loading state (reuse the `recompiling`-style pattern). A "Re-run" control hits `?refresh=true`.
- **Ad-hoc:** a small "Critique a file" panel (file input, `.pdf`/`.docx`) → `POST /critic/adhoc` → render the same result view. No workspace is created.
- **Rendering per section:** title, an **AI-genericness gauge** (0–100, colored: green < 35, amber 35–65, red > 65) with the `heuristic`/`model` breakdown, the 3 criticisms (category chip + issue + suggestion), the detected `ai_signals`, and the `deai_tips` as a checklist. A header shows `overall_ai_score`, the `summary`, and which **provider** produced it.
- `api.ts`: `fetchProviders()`, `fetchCritique(id)`, `runCritique(id, refresh?)`, `critiqueAdhoc(file)` + types mirroring §5.

---

## 8. Files affected (implementation reference)

| File | Change |
|---|---|
| `src/critic/__init__.py`, `models.py`, `heuristics.py`, `textprep.py`, `pipeline.py` | **new** — core analysis (provider-agnostic) |
| `src/critic/providers/{__init__,base,claude,ollama,cerebras}.py` | **new** — provider abstraction + factory |
| `src/critic/config.py` | **new** — env-driven provider/model selection |
| `src/docserver/main.py` | add the 4 endpoints in §6 |
| `src/docserver/schemas.py` | re-export critic schemas |
| `pyproject.toml` | add `anthropic`, `pypdf`; keep provider SDKs optional/lazy |
| `web/src/api.ts`, `web/src/App.tsx`, `web/src/App.css` | Critic tab, ad-hoc panel, gauge + result rendering |

---

## 9. Verification plan

- **Unit (no network):** `heuristics.py` on hand-written samples — a deliberately "AI-sounding" paragraph (filler + uniform sentences) scores high; a varied human paragraph scores low. `strip_latex()` removes commands/math and keeps prose. A **mock provider** drives `pipeline.py` end to end and asserts exactly 3 criticisms, a 0–100 combined score, and the heuristic/model breakdown.
- **API:** `POST /documents/{id}/critique` on a converted doc returns one `SectionCritique` per manifest section and writes `critique.json`; `GET` returns the cache; `POST /critic/adhoc` with a small `.pdf` and a `.docx` both return a `CritiqueResult`; `GET /critic/providers` lists the configured provider.
- **Provider smoke (manual, opt-in):** with `CRITIC_PROVIDER=ollama` against the Windows-host model, and (if keys present) `claude` / `cerebras`, run one section and eyeball quality. Keep this out of CI (needs creds/network).
- **E2E:** `./scripts/start_web.sh`, open a document, run the Critic tab, confirm per-section gauges + criticisms + de-AI tips render and the provider name is shown; upload a standalone PDF via the ad-hoc panel.

---

## 10. Non-goals / risks

- Not a plagiarism or AI-**detection** classifier; the AI-genericness score is a **writing-quality heuristic**, explicitly labeled as such in the UI (avoid implying it "detects AI authorship").
- No automatic rewriting of the paper — the Critic only advises. (A future "apply tip" action could reuse the existing section-edit endpoint.)
- Cost/latency scale with section count × provider; mitigated by per-document caching, concurrency, and prompt caching on the Claude rubric. Per-section failures degrade gracefully rather than failing the whole run.
