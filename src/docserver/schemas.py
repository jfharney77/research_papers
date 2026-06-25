from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# Re-exported so docserver consumers import template schemas from one place.
from docbuilder.models import TemplateInfo, TemplateListResponse  # noqa: F401


class SectionResponse(BaseModel):
    section_id: str
    title: str
    level: int
    slug: str
    latex_path: str
    order: int


class FigureResponse(BaseModel):
    figure_id: str
    caption: str | None
    relative_path: str
    section_slug: str


class BuildResponse(BaseModel):
    status: Literal["pending", "succeeded", "failed"]
    last_run: datetime | None = None
    pdf_path: str | None = None
    log_path: str | None = None
    message: str | None = None


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    template: str
    source_docx: str
    created_at: datetime
    sections: list[SectionResponse]
    figures: list[FigureResponse]
    build: BuildResponse
    references_warning: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class CreateDocumentResponse(BaseModel):
    document: DocumentResponse


class CompileResponse(BaseModel):
    status: str
    build: BuildResponse


class SectionUpdate(BaseModel):
    content: str


def read_manifest(manifest_path: Path) -> DocumentResponse:
    data = json.loads(manifest_path.read_text())
    return DocumentResponse(**data)


import json  # placed at end to avoid circular import during type checking
