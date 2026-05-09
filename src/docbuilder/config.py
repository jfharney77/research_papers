from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LATEX_ROOT = REPO_ROOT / "latex"
SCRIPT_ROOT = REPO_ROOT / "script" / "latex"
DOCUMENTS_ROOT = REPO_ROOT / "documents"

DEFAULT_TEMPLATE = "ieee"

__all__ = [
    "REPO_ROOT",
    "LATEX_ROOT",
    "SCRIPT_ROOT",
    "DOCUMENTS_ROOT",
    "DEFAULT_TEMPLATE",
]
