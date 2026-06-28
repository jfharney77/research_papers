"""Orchestrates heuristics + provider into per-section and per-document critiques."""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from docbuilder.config import DOCUMENTS_ROOT, validate_document_id

from .config import RUBRIC
from .heuristics import compute_heuristics
from .models import CritiqueResult, SectionCritique
from .providers import CritiqueProvider, get_provider
from .textprep import RawSection, sections_from_upload, strip_latex

logger = logging.getLogger(__name__)


def _critique_one(*, slug: str, title: str, prose: str, provider: CritiqueProvider) -> SectionCritique:
    report = compute_heuristics(prose)
    try:
        llm = provider.analyze_section(rubric=RUBRIC, prose=prose, signals=report.signals)
    except Exception:  # one section failing should not sink the whole run
        logger.warning("Provider failed on section %r; using offline stub.", slug, exc_info=True)
        from .providers.stub import StubProvider

        llm = StubProvider().analyze_section(rubric=RUBRIC, prose=prose, signals=report.signals)

    criticisms = list(llm.criticisms)[:3]
    while len(criticisms) < 3:  # schema guarantees exactly 3
        from .models import Criticism

        criticisms.append(
            Criticism(category="clarity", issue="(no further issue identified)", suggestion="—")
        )

    ai_score = round(0.5 * report.ai_score + 0.5 * max(0, min(100, llm.ai_score_model)))
    return SectionCritique(
        section_slug=slug,
        title=title,
        criticisms=criticisms,
        ai_score=ai_score,
        ai_score_breakdown={"heuristic": report.ai_score, "model": int(llm.ai_score_model)},
        ai_signals=report.signals,
        deai_tips=list(llm.deai_tips),
    )


def _summarize(sections: list[SectionCritique]) -> tuple[int, str]:
    if not sections:
        return 0, "No sections to assess."
    overall = round(sum(s.ai_score for s in sections) / len(sections))
    cats = Counter(c.category for s in sections for c in s.criticisms)
    top = ", ".join(f"{cat} ({n})" for cat, n in cats.most_common(3))
    return overall, (
        f"Mean AI-genericness {overall}/100 across {len(sections)} section(s). "
        f"Most common critique areas: {top}."
    )


def _build_result(
    *, document_id: str | None, raw: list[RawSection], provider: CritiqueProvider, is_latex: bool
) -> CritiqueResult:
    sections = [
        _critique_one(
            slug=r.slug,
            title=r.title,
            prose=strip_latex(r.text) if is_latex else r.text,
            provider=provider,
        )
        for r in raw
        if r.text.strip()
    ]
    overall, summary = _summarize(sections)
    return CritiqueResult(
        document_id=document_id,
        provider=provider.name,
        overall_ai_score=overall,
        summary=summary,
        sections=sections,
    )


# --- Workspace documents -----------------------------------------------------

def _critique_path(document_id: str) -> Path:
    validate_document_id(document_id)
    return DOCUMENTS_ROOT / document_id / "critique.json"


def load_cached(document_id: str) -> CritiqueResult | None:
    path = _critique_path(document_id)
    if not path.exists():
        return None
    return CritiqueResult.model_validate_json(path.read_text())


def critique_document(
    document_id: str, *, provider: CritiqueProvider | None = None, refresh: bool = False
) -> CritiqueResult:
    validate_document_id(document_id)
    workspace = DOCUMENTS_ROOT / document_id
    manifest_path = workspace / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"document {document_id} not found")

    if not refresh:
        cached = load_cached(document_id)
        if cached is not None:
            return cached

    manifest = json.loads(manifest_path.read_text())
    template = manifest["template"]
    raw: list[RawSection] = []
    for s in manifest.get("sections", []):
        tex_path = workspace / template / s["latex_path"]
        text = tex_path.read_text() if tex_path.exists() else ""
        raw.append(RawSection(title=s["title"], slug=s["slug"], text=text))

    provider = provider or get_provider()
    result = _build_result(document_id=document_id, raw=raw, provider=provider, is_latex=True)
    _critique_path(document_id).write_text(result.model_dump_json(indent=2))
    return result


# --- Ad-hoc uploads ----------------------------------------------------------

def critique_adhoc(filename: str, data: bytes, *, provider: CritiqueProvider | None = None) -> CritiqueResult:
    raw = sections_from_upload(filename, data)
    provider = provider or get_provider()
    return _build_result(document_id=None, raw=raw, provider=provider, is_latex=False)
