"""Single entry point for the Research Paper Workspace (Word → LaTeX tool).

Run the product backend:

    python main.py            # serves the doc server on :8000
    DOCSERVER_PORT=9000 python main.py

For the full stack (backend + React dev server) use ``scripts/start_web.sh``.
The unrelated APIP research simulation lives under ``research/`` and is launched
separately via ``research/run_apip.sh``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# src-layout: make the product packages importable without installation.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main() -> None:
    import uvicorn

    uvicorn.run(
        "docserver.main:app",
        host=os.environ.get("DOCSERVER_HOST", "0.0.0.0"),
        port=int(os.environ.get("DOCSERVER_PORT", "8000")),
        reload=bool(os.environ.get("DOCSERVER_RELOAD")),
    )


if __name__ == "__main__":
    main()
