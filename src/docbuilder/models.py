from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class FigureEntry(BaseModel):
    figure_id: str
    caption: str | None = None
    relative_path: str
    section_slug: str


class SectionEntry(BaseModel):
    section_id: str
    title: str
    level: int
    slug: str
    latex_path: str
    order: int


class BuildInfo(BaseModel):
    status: Literal["pending", "succeeded", "failed"] = "pending"
    last_run: datetime | None = None
    pdf_path: str | None = None
    log_path: str | None = None
    message: str | None = None


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str | None = None
    buildable: bool = True


class TemplateListResponse(BaseModel):
    templates: list[TemplateInfo]
    default: str


class DocumentManifest(BaseModel):
    document_id: str
    title: str
    template: str
    source_docx: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sections: list[SectionEntry] = Field(default_factory=list)
    figures: list[FigureEntry] = Field(default_factory=list)
    build: BuildInfo = Field(default_factory=BuildInfo)
    references_warning: str | None = None

    @property
    def workspace(self) -> Path:
        raise AttributeError("Workspace path is not stored in the manifest. Pass explicitly.")
