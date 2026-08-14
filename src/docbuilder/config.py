from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LATEX_ROOT = REPO_ROOT / "templates" / "latex"
SCRIPT_ROOT = REPO_ROOT / "scripts" / "templates"
DOCUMENTS_ROOT = REPO_ROOT / "documents"

DEFAULT_TEMPLATE = "ieee"


# --- Document-id validation --------------------------------------------------
# document_id arrives from URL path parameters and is joined directly to
# DOCUMENTS_ROOT. A strict allowlist stops path traversal (``..``, separators,
# absolute prefixes) before any filesystem operation can escape the root.
# Legitimate ids are produced by ``snake_case(stem)`` in the converter, so they
# only ever contain letters, digits, and underscores.
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_document_id(document_id: str) -> None:
    """Raise ValueError if document_id could traverse outside DOCUMENTS_ROOT."""
    if not document_id or not _SAFE_ID.match(document_id):
        raise ValueError(
            f"Invalid document_id {document_id!r}: "
            "must be non-empty and contain only letters, digits, hyphens, or underscores."
        )


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


# --- LaTeX build sandbox -----------------------------------------------------
# The build path compiles attacker-influenceable .tex, so it is constrained.
# "local" = hardened subprocess (rlimits + restricted TeX file IO + timeout);
# "docker" = run the build inside a throwaway container (strongest isolation).
LATEX_SANDBOX = os.environ.get("LATEX_SANDBOX", "local").strip().lower()
LATEX_DOCKER_IMAGE = os.environ.get("LATEX_DOCKER_IMAGE", "texlive/texlive:latest")
LATEX_BUILD_TIMEOUT = _int_env("LATEX_BUILD_TIMEOUT", 120)        # wall-clock seconds
LATEX_CPU_SECONDS = _int_env("LATEX_CPU_SECONDS", 60)            # RLIMIT_CPU
LATEX_MAX_MEMORY_MB = _int_env("LATEX_MAX_MEMORY_MB", 2048)      # RLIMIT_AS
LATEX_MAX_OUTPUT_MB = _int_env("LATEX_MAX_OUTPUT_MB", 50)        # RLIMIT_FSIZE
# When false, the build scripts will NOT apt-get install TeX Live on the host.
LATEX_AUTO_INSTALL = os.environ.get("LATEX_AUTO_INSTALL", "0").strip() in {"1", "true", "yes"}

__all__ = [
    "REPO_ROOT",
    "LATEX_ROOT",
    "SCRIPT_ROOT",
    "DOCUMENTS_ROOT",
    "DEFAULT_TEMPLATE",
    "validate_document_id",
    "LATEX_SANDBOX",
    "LATEX_DOCKER_IMAGE",
    "LATEX_BUILD_TIMEOUT",
    "LATEX_CPU_SECONDS",
    "LATEX_MAX_MEMORY_MB",
    "LATEX_MAX_OUTPUT_MB",
    "LATEX_AUTO_INSTALL",
]
