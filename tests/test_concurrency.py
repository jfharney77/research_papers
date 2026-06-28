"""Event-loop responsiveness tests for the two upload handlers.

These guard the fix that converts ``create_document`` and
``critique_adhoc_upload`` from ``async def`` (which run on the event loop
thread and block all other requests during a LaTeX build or LLM call) back to
plain ``def`` (which FastAPI dispatches to its anyio thread pool).
"""

from __future__ import annotations

import inspect
import io
import time

import anyio
import httpx
import pytest
from httpx import ASGITransport

from docbuilder.converter import ConversionError
from docserver import main
from docserver.main import app, create_document, critique_adhoc_upload


# ---------------------------------------------------------------------------
# Handlers must be plain ``def`` so FastAPI offloads them to the thread pool.
# ---------------------------------------------------------------------------

def test_upload_handlers_are_sync_def():
    assert not inspect.iscoroutinefunction(create_document)
    assert not inspect.iscoroutinefunction(critique_adhoc_upload)


# ---------------------------------------------------------------------------
# A blocking build must not freeze the event loop: /health stays responsive.
# ---------------------------------------------------------------------------

def test_health_responds_while_create_document_blocks(monkeypatch):
    def _slow_convert(*args, **kwargs):
        time.sleep(2)
        raise ConversionError("blocked on purpose")

    monkeypatch.setattr(main, "convert_upload", _slow_convert)

    async def scenario():
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            files = {"file": ("paper.docx", io.BytesIO(b"PK\x03\x04stub"), "application/octet-stream")}

            async def fire_build():
                # Long-running upload; result is irrelevant to this test.
                await ac.post("/documents", files=files, params={"build_pdf": False})

            async with anyio.create_task_group() as tg:
                tg.start_soon(fire_build)
                # Give the build a moment to start occupying a worker thread.
                await anyio.sleep(0.2)
                start = time.perf_counter()
                res = await ac.get("/health")
                elapsed = time.perf_counter() - start

        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
        # If the handler still ran on the event loop, /health would wait ~2s.
        assert elapsed < 1.0

    anyio.run(scenario)


# ---------------------------------------------------------------------------
# Two simultaneous uploads make progress concurrently rather than serializing.
# ---------------------------------------------------------------------------

def test_two_create_documents_run_concurrently(monkeypatch):
    def _slow_convert(*args, **kwargs):
        time.sleep(1)
        raise ConversionError("blocked on purpose")

    monkeypatch.setattr(main, "convert_upload", _slow_convert)

    async def scenario():
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            files = {"file": ("paper.docx", io.BytesIO(b"PK\x03\x04stub"), "application/octet-stream")}

            async def fire():
                return await ac.post("/documents", files=files, params={"build_pdf": False})

            start = time.perf_counter()
            results = []
            async with anyio.create_task_group() as tg:
                async def collect():
                    results.append(await fire())

                tg.start_soon(collect)
                tg.start_soon(collect)
            elapsed = time.perf_counter() - start

        assert all(r.status_code == 400 for r in results)
        # Serialized execution would take ~2s; concurrent ~1s.
        assert elapsed < 1.8

    anyio.run(scenario)


# ---------------------------------------------------------------------------
# file.file.read() returns the same bytes the async await file.read() did.
# ---------------------------------------------------------------------------

def test_uploadfile_sync_read_round_trips():
    from fastapi import UploadFile

    payload = b"some fixture bytes \x00\x01\x02 round-trip"
    upload = UploadFile(filename="f.docx", file=io.BytesIO(payload))
    assert upload.file.read() == payload
