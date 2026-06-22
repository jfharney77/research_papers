from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LATEX_ROOT = REPO_ROOT / "latex"
SCRIPT_ROOT = REPO_ROOT / "script" / "latex"
DOCUMENTS_ROOT = REPO_ROOT / "documents"

DEFAULT_TEMPLATE = "ieee"


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
    "LATEX_SANDBOX",
    "LATEX_DOCKER_IMAGE",
    "LATEX_BUILD_TIMEOUT",
    "LATEX_CPU_SECONDS",
    "LATEX_MAX_MEMORY_MB",
    "LATEX_MAX_OUTPUT_MB",
    "LATEX_AUTO_INSTALL",
]
