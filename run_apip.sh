#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "Installing dependencies..."
uv sync

echo "Starting APIP simulation server..."
uv run uvicorn src.apip.backend.main:app --reload --host 0.0.0.0 --port 8000
