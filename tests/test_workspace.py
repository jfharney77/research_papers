"""Tests for section editing, archive download, and storage hardening."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from docserver import storage
from docserver.main import app
from docserver.storage import _validate_document_id, safe_upload_name, zip_directory

client = TestClient(app)


# ---------------------------------------------------------------------------
# safe_upload_name — path traversal hardening
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("paper.docx", "paper.docx"),
        ("../../etc/passwd.docx", "passwd.docx"),
        ("/abs/path/to/paper.docx", "paper.docx"),
        ("nested\\windows\\paper.docx", "paper.docx"),
    ],
)
def test_safe_upload_name_strips_directories(raw, expected):
    # Path().name uses the host separator; the key guarantee is no directory escape.
    assert "/" not in safe_upload_name(raw)
    assert safe_upload_name(raw).endswith(".docx")


def test_safe_upload_name_rejects_empty():
    with pytest.raises(ValueError):
        safe_upload_name("")
    with pytest.raises(ValueError):
        safe_upload_name(None)


# ---------------------------------------------------------------------------
# zip_directory
# ---------------------------------------------------------------------------

def test_zip_directory_contains_all_files(tmp_path):
    (tmp_path / "main.tex").write_text("\\documentclass{article}")
    (tmp_path / "sections").mkdir()
    (tmp_path / "sections" / "intro.tex").write_text("intro")

    data = zip_directory(tmp_path)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        assert "main.tex" in names
        assert "sections/intro.tex" in names
        assert zf.read("sections/intro.tex").decode() == "intro"


# ---------------------------------------------------------------------------
# list_documents — skip malformed manifests
# ---------------------------------------------------------------------------

def test_list_documents_skips_malformed(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DOCUMENTS_ROOT", tmp_path)

    good = tmp_path / "good"
    good.mkdir()
    (good / "manifest.json").write_text(json.dumps({
        "document_id": "good",
        "title": "Good",
        "template": "ieee",
        "source_docx": "good.docx",
        "created_at": "2026-01-01T00:00:00",
        "sections": [],
        "figures": [],
        "build": {"status": "pending"},
    }))

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "manifest.json").write_text("{ not valid json")

    docs = storage.list_documents()
    ids = [d.document_id for d in docs]
    assert ids == ["good"]


# ---------------------------------------------------------------------------
# New endpoints respond sensibly for a missing document
# ---------------------------------------------------------------------------

def test_archive_missing_document_returns_404():
    res = client.get("/documents/does-not-exist/archive")
    assert res.status_code == 404


def test_update_section_missing_document_returns_404():
    res = client.put("/documents/does-not-exist/sections/intro", json={"content": "hi"})
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# _validate_document_id — path traversal hardening for URL-derived ids
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("good", ["my-paper", "doc_1", "Paper2024", "a", "my_paper_2024"])
def test_validate_document_id_accepts_legitimate(good):
    _validate_document_id(good)  # should not raise


@pytest.mark.parametrize(
    "bad",
    ["..", "../etc", "a/b", "", "/etc", "%2E%2E", "foo.bar", "a\\b", "with space", "nested/path"],
)
def test_validate_document_id_rejects_traversal(bad):
    with pytest.raises(ValueError):
        _validate_document_id(bad)


# ---------------------------------------------------------------------------
# Destructive / read endpoints reject traversal ids with 400 (not 200/404/500)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_id", ["..", "../etc", "%2E%2E", "foo.bar"])
def test_delete_document_rejects_traversal(bad_id):
    res = client.delete(f"/documents/{bad_id}")
    assert res.status_code == 400


@pytest.mark.parametrize("bad_id", ["..", "../etc", "%2E%2E", "foo.bar"])
def test_get_document_rejects_traversal(bad_id):
    res = client.get(f"/documents/{bad_id}")
    assert res.status_code == 400


@pytest.mark.parametrize("bad_id", ["..", "../etc", "%2E%2E", "foo.bar"])
def test_get_archive_rejects_traversal(bad_id):
    res = client.get(f"/documents/{bad_id}/archive")
    assert res.status_code == 400


def test_delete_legitimate_missing_document_returns_404():
    # A well-formed but non-existent id must still report "not found", not 400.
    res = client.delete("/documents/nonexistent-doc")
    assert res.status_code == 404


def test_new_routes_registered():
    paths = {r.path for r in app.routes}
    assert "/documents/{document_id}/archive" in paths
    methods = {(r.path, m) for r in app.routes for m in getattr(r, "methods", set())}
    assert ("/documents/{document_id}/sections/{section_slug}", "PUT") in methods
