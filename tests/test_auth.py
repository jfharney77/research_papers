"""Tests for doc server authentication and CORS configuration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from docserver.main import _cors_origins, app

client = TestClient(app)
KEY = "test-secret-key"


def test_cors_is_not_wildcard():
    assert "*" not in _cors_origins
    assert _cors_origins  # at least the local dev origin


def test_auth_disabled_when_key_unset(monkeypatch):
    monkeypatch.delenv("DOCSERVER_API_KEY", raising=False)
    assert client.get("/templates").status_code == 200


def test_auth_required_when_key_set(monkeypatch):
    monkeypatch.setenv("DOCSERVER_API_KEY", KEY)
    assert client.get("/templates").status_code == 401


def test_auth_accepts_bearer_header(monkeypatch):
    monkeypatch.setenv("DOCSERVER_API_KEY", KEY)
    res = client.get("/templates", headers={"Authorization": f"Bearer {KEY}"})
    assert res.status_code == 200


def test_auth_accepts_x_api_key_header(monkeypatch):
    monkeypatch.setenv("DOCSERVER_API_KEY", KEY)
    res = client.get("/templates", headers={"X-API-Key": KEY})
    assert res.status_code == 200


def test_auth_accepts_query_param(monkeypatch):
    monkeypatch.setenv("DOCSERVER_API_KEY", KEY)
    res = client.get(f"/templates?api_key={KEY}")
    assert res.status_code == 200


def test_auth_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("DOCSERVER_API_KEY", KEY)
    res = client.get("/templates", headers={"Authorization": "Bearer nope"})
    assert res.status_code == 401


def test_health_is_exempt(monkeypatch):
    monkeypatch.setenv("DOCSERVER_API_KEY", KEY)
    assert client.get("/health").status_code == 200
