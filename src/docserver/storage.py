from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable

from fastapi import UploadFile

from docbuilder.config import DOCUMENTS_ROOT
from docbuilder.converter import ConversionOptions, convert_document

from .schemas import DocumentResponse, read_manifest


def list_documents() -> list[DocumentResponse]:
    if not DOCUMENTS_ROOT.exists():
        return []
    manifests: list[DocumentResponse] = []
    for manifest_path in DOCUMENTS_ROOT.glob("*/manifest.json"):
        manifests.append(read_manifest(manifest_path))
    return sorted(manifests, key=lambda m: m.created_at, reverse=True)


def load_document(document_id: str) -> DocumentResponse:
    manifest_path = DOCUMENTS_ROOT / document_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"document {document_id} not found")
    return read_manifest(manifest_path)


def save_upload(upload: UploadFile, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as fh:
        fh.write(upload.file.read())
    return destination


def convert_upload(*, upload: UploadFile, template: str, build_pdf: bool, overwrite: bool = False) -> DocumentResponse:
    temp_path = DOCUMENTS_ROOT / "_uploads" / upload.filename
    save_upload(upload, temp_path)
    try:
        manifest = convert_document(temp_path, ConversionOptions(template=template, build_pdf=build_pdf, overwrite=overwrite))
    finally:
        if temp_path.exists():
            temp_path.unlink()
    manifest_path = DOCUMENTS_ROOT / manifest.document_id / "manifest.json"
    return read_manifest(manifest_path)


def delete_document(document_id: str) -> None:
    target = DOCUMENTS_ROOT / document_id
    if not target.exists():
        raise FileNotFoundError(f"document {document_id} not found")
    shutil.rmtree(target)
