from __future__ import annotations

import os

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from .auth import require_api_key

from docbuilder.config import DEFAULT_TEMPLATE, DOCUMENTS_ROOT
from docbuilder.converter import ConversionError, ConversionOptions, convert_document, rebuild_pdf
from docbuilder.templates import available_templates, is_valid_template, valid_template_ids

from .schemas import (
    CompileResponse,
    CreateDocumentResponse,
    DocumentListResponse,
    DocumentResponse,
    SectionResponse,
    SectionUpdate,
    TemplateListResponse,
)
from .storage import (
    convert_upload,
    delete_document,
    list_documents,
    load_document,
    zip_directory,
)

app = FastAPI(title="Research Paper Workspace API", dependencies=[Depends(require_api_key)])

# Restrict CORS to explicitly configured origins (default: the local Vite dev
# server). Override with DOCSERVER_CORS_ORIGINS="https://a.com,https://b.com".
_cors_origins = [
    o.strip()
    for o in os.environ.get(
        "DOCSERVER_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/templates", response_model=TemplateListResponse)
def get_templates():
    return TemplateListResponse(templates=available_templates(), default=DEFAULT_TEMPLATE)


@app.get("/documents", response_model=DocumentListResponse)
def get_documents():
    documents = list_documents()
    return DocumentListResponse(documents=documents)


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str):
    try:
        return load_document(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")


@app.delete("/documents/{document_id}")
def remove_document(document_id: str):
    try:
        delete_document(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "document_id": document_id}


@app.get("/documents/{document_id}/sections", response_model=list[SectionResponse])
def get_sections(document_id: str):
    manifest = get_document(document_id)
    return manifest.sections


@app.get("/documents/{document_id}/sections/{section_slug}", response_class=PlainTextResponse)
def get_section_source(document_id: str, section_slug: str):
    manifest = get_document(document_id)
    try:
        section = next(s for s in manifest.sections if s.slug == section_slug)
    except StopIteration:
        raise HTTPException(status_code=404, detail="Section not found")

    section_path = DOCUMENTS_ROOT / document_id / manifest.template / section.latex_path
    if not section_path.exists():
        raise HTTPException(status_code=404, detail="Section file missing")
    return PlainTextResponse(section_path.read_text(), media_type="text/x-latex")


@app.put("/documents/{document_id}/sections/{section_slug}")
def update_section_source(document_id: str, section_slug: str, body: SectionUpdate):
    manifest = get_document(document_id)
    try:
        section = next(s for s in manifest.sections if s.slug == section_slug)
    except StopIteration:
        raise HTTPException(status_code=404, detail="Section not found")

    section_path = DOCUMENTS_ROOT / document_id / manifest.template / section.latex_path
    if not section_path.exists():
        raise HTTPException(status_code=404, detail="Section file missing")
    section_path.write_text(body.content)
    return {"status": "saved", "section_slug": section_slug}


@app.post("/documents", response_model=CreateDocumentResponse)
async def create_document(
    file: UploadFile = File(...),
    template: str = DEFAULT_TEMPLATE,
    build_pdf: bool = True,
    overwrite: bool = False,
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx uploads are supported")

    if not is_valid_template(template):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template '{template}'. Valid templates: {', '.join(valid_template_ids())}",
        )

    try:
        document = convert_upload(upload=file, template=template, build_pdf=build_pdf, overwrite=overwrite)
    except ConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CreateDocumentResponse(document=document)


@app.post("/documents/{document_id}/compile", response_model=CompileResponse)
def recompile_document(document_id: str):
    manifest_path = DOCUMENTS_ROOT / document_id / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        manifest = rebuild_pdf(document_id)
    except ConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CompileResponse(status="ok", build=manifest.build)


@app.get("/documents/{document_id}/pdf")
def get_pdf(document_id: str):
    manifest = load_document(document_id)
    if not manifest.build.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available")
    pdf_path = DOCUMENTS_ROOT / document_id / manifest.build.pdf_path
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing")
    return FileResponse(pdf_path)


@app.get("/documents/{document_id}/archive")
def get_archive(document_id: str):
    try:
        manifest = load_document(document_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    workspace = DOCUMENTS_ROOT / document_id / manifest.template
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="LaTeX workspace not found")
    data = zip_directory(workspace)
    filename = f"{document_id}_{manifest.template}_latex.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/documents/{document_id}/log", response_class=PlainTextResponse)
def get_build_log(document_id: str):
    manifest = load_document(document_id)
    if not manifest.build.log_path:
        raise HTTPException(status_code=404, detail="No build log available")
    log_path = DOCUMENTS_ROOT / document_id / manifest.build.log_path
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Build log file missing")
    return PlainTextResponse(log_path.read_text(), media_type="text/plain")


@app.get("/documents/{document_id}/word")
def get_word(document_id: str):
    manifest = load_document(document_id)
    docx_path = DOCUMENTS_ROOT / document_id / manifest.source_docx
    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="Original docx missing")
    return FileResponse(docx_path)
