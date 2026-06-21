"""Tests for the template registry, the /templates endpoint, and template validation."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from docbuilder.cli import app as cli_app
from docbuilder.config import DEFAULT_TEMPLATE
from docbuilder.templates import (
    available_templates,
    is_buildable,
    is_valid_template,
    valid_template_ids,
)
from docserver.main import app

EXPECTED_TEMPLATES = {"aaai", "acm", "ieee", "neurips"}

client = TestClient(app)
runner = CliRunner()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_available_templates_discovers_known_templates():
    ids = {t.id for t in available_templates()}
    assert EXPECTED_TEMPLATES <= ids


def test_known_templates_are_buildable():
    for t in available_templates():
        if t.id in EXPECTED_TEMPLATES:
            assert t.buildable, f"{t.id} should have a build script"


def test_template_info_has_display_name():
    by_id = {t.id: t for t in available_templates()}
    assert by_id["ieee"].name == "IEEE Conference"
    assert by_id["ieee"].description


def test_validation_helpers():
    assert is_valid_template("ieee")
    assert not is_valid_template("bogus")
    assert is_buildable("ieee")
    assert DEFAULT_TEMPLATE in valid_template_ids()


# ---------------------------------------------------------------------------
# GET /templates
# ---------------------------------------------------------------------------

def test_templates_endpoint():
    res = client.get("/templates")
    assert res.status_code == 200
    body = res.json()
    assert body["default"] == DEFAULT_TEMPLATE
    ids = {t["id"] for t in body["templates"]}
    assert EXPECTED_TEMPLATES <= ids
    for t in body["templates"]:
        assert set(t) >= {"id", "name", "buildable"}


# ---------------------------------------------------------------------------
# POST /documents validation (negative paths — no real conversion)
# ---------------------------------------------------------------------------

def _fake_docx(name: str = "paper.docx"):
    return {"file": (name, io.BytesIO(b"not a real docx"), "application/octet-stream")}


def test_upload_rejects_unknown_template():
    res = client.post("/documents?template=bogus&build_pdf=false", files=_fake_docx())
    assert res.status_code == 400
    assert "bogus" in res.json()["detail"]
    assert "ieee" in res.json()["detail"]


def test_upload_rejects_non_docx():
    res = client.post("/documents?template=ieee", files=_fake_docx("notes.txt"))
    assert res.status_code == 400
    assert ".docx" in res.json()["detail"]


# ---------------------------------------------------------------------------
# CLI validation
# ---------------------------------------------------------------------------

def test_cli_rejects_unknown_template(tmp_path):
    dummy = tmp_path / "paper.docx"
    dummy.write_bytes(b"stub")
    result = runner.invoke(cli_app, [str(dummy), "--template", "bogus"])
    assert result.exit_code == 1
    assert "bogus" in result.output


def test_cli_accepts_known_template_argument(tmp_path):
    # A valid template passes validation; conversion then fails on the stub docx,
    # which is enough to confirm the template gate let it through.
    dummy = tmp_path / "paper.docx"
    dummy.write_bytes(b"stub")
    result = runner.invoke(cli_app, [str(dummy), "--template", "ieee", "--no-build"])
    assert "Invalid template" not in result.output
