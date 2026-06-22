from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["substance", "clarity", "structure", "rigor", "style"]


class Criticism(BaseModel):
    category: Category
    issue: str
    suggestion: str


class SectionLLMResult(BaseModel):
    """The provider-produced slice of a section critique."""

    criticisms: list[Criticism]
    ai_score_model: int  # 0-100, how generically "AI" the prose reads
    deai_tips: list[str]


class SectionCritique(BaseModel):
    section_slug: str
    title: str
    criticisms: list[Criticism]
    ai_score: int                       # combined heuristic + model, 0-100
    ai_score_breakdown: dict[str, int]  # {"heuristic": int, "model": int}
    ai_signals: list[str]
    deai_tips: list[str]


class CritiqueResult(BaseModel):
    document_id: str | None = None
    provider: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    overall_ai_score: int
    summary: str
    sections: list[SectionCritique]


class ProviderInfo(BaseModel):
    id: str
    available: bool
    active: bool


class ProviderListResponse(BaseModel):
    providers: list[ProviderInfo]
    active: str
