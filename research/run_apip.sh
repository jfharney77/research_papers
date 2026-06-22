#!/usr/bin/env bash
# Launches the APIP research simulation (a separate app from the Word→LaTeX
# product). Runs from the repo root so the package resolves; uses port 8100 so
# it never collides with the product server on :8000.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "Installing dependencies..."
uv sync

echo "Starting APIP simulation server on :8100 ..."
uv run uvicorn research.apip_sim.backend.main:app --reload --host 0.0.0.0 --port 8100
