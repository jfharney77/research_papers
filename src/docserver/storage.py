from __future__ import annotations

import io
import logging
import shutil
import zipfile
from pathlib import Path

from fastapi import UploadFile

from docbuilder.config import DOCUMENTS_ROOT, validate_document_id
from docbuilder.converter import ConversionOptions, convert_document

from .schemas import DocumentResponse, read_manifest

logger = logging.getLogger(__name__)


def list_documents() -> list[DocumentResponse]:
    if not DOCUMENTS_ROOT.exists():
        return []
    manifests: list[DocumentResponse] = []
    for manifest_path in DOCUMENTS_ROOT.glob("*/manifest.json"):
        try:
            manifests.append(read_manifest(manifest_path))
        except Exception:  # malformed/partial manifest — skip rather than fail the whole list
            logger.warning("Skipping unreadable manifest: %s", manifest_path, exc_info=True)
    return sorted(manifests, key=lambda m: m.created_at, reverse=True)


def safe_upload_name(filename: str | None) -> str:
    """Strip any directory components from an uploaded filename to prevent path traversal."""
    name = Path(filename or "").name
    if not name:
        raise ValueError("Upload is missing a filename")
    return name


# Re-exported under the storage namespace so callers (and tests) can validate a
# document_id at the storage boundary; canonical definition lives in docbuilder.config.
_validate_document_id = validate_document_id


def load_document(document_id: str) -> DocumentResponse:
    _validate_document_id(document_id)
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
    temp_path = DOCUMENTS_ROOT / "_uploads" / safe_upload_name(upload.filename)
    save_upload(upload, temp_path)
    try:
        manifest = convert_document(temp_path, ConversionOptions(template=template, build_pdf=build_pdf, overwrite=overwrite))
    finally:
        if temp_path.exists():
            temp_path.unlink()
    manifest_path = DOCUMENTS_ROOT / manifest.document_id / "manifest.json"
    return read_manifest(manifest_path)


def zip_directory(root: Path) -> bytes:
    """Zip every file under ``root`` into an in-memory archive, paths relative to ``root``."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(root).as_posix())
    return buffer.getvalue()


def delete_document(document_id: str) -> None:
    _validate_document_id(document_id)
    target = DOCUMENTS_ROOT / document_id
    if not target.exists():
        raise FileNotFoundError(f"document {document_id} not found")
    shutil.rmtree(target)
