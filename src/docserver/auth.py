"""API-key authentication for the doc server.

The build path turns uploads into compiled PDFs, so the API must not be open.
Set ``DOCSERVER_API_KEY`` and every request (except health/docs) must present it
as ``Authorization: Bearer <key>`` or ``X-API-Key: <key>``.

If the variable is unset the server logs a loud warning and allows requests, so
local development and the test suite work without ceremony — but production
deployments MUST set it.
"""

from __future__ import annotations

import hmac
import logging
import os

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

_EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}
_warned = False


def _configured_key() -> str | None:
    return os.environ.get("DOCSERVER_API_KEY") or None


def _extract_key(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    # Query-param fallback for browser GETs that can't set headers
    # (PDF <iframe src>, download <a href>).
    qp = request.query_params.get("api_key")
    return qp.strip() if qp else None


def require_api_key(request: Request) -> None:
    global _warned
    key = _configured_key()
    if not key:
        if not _warned:
            logger.warning(
                "DOCSERVER_API_KEY is not set — API authentication is DISABLED. "
                "Set it before exposing this server beyond localhost."
            )
            _warned = True
        return
    if request.url.path in _EXEMPT_PATHS:
        return
    provided = _extract_key(request)
    if not provided or not hmac.compare_digest(provided, key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
