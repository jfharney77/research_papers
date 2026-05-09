#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs"
PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"
BACKEND_PID_FILE="${LOG_DIR}/.backend.pid"
FRONTEND_PID_FILE="${LOG_DIR}/.frontend.pid"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

mkdir -p "$LOG_DIR"

ensure_not_running() {
  local name=$1
  local pid_file=$2
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" && -d "/proc/$pid" ]]; then
      echo "${name} already running (pid $pid). Stop it before starting a new session." >&2
      exit 1
    fi
    rm -f "$pid_file"
  fi
}

ensure_not_running "Backend" "$BACKEND_PID_FILE"
ensure_not_running "Frontend" "$FRONTEND_PID_FILE"

run_backend() {
  local cmd
  if command -v uv >/dev/null 2>&1; then
    cmd=(env PYTHONPATH="$PYTHONPATH" uv run uvicorn docserver.main:app --host 0.0.0.0 --port 8000)
  else
    cmd=(env PYTHONPATH="$PYTHONPATH" python -m uvicorn docserver.main:app --host 0.0.0.0 --port 8000)
  fi
  (cd "$REPO_ROOT" && nohup "${cmd[@]}" >"$BACKEND_LOG" 2>&1 & echo $! >"$BACKEND_PID_FILE")
  echo "Backend running → $(cat "$BACKEND_PID_FILE") (logs: $BACKEND_LOG)"
}

run_frontend() {
  (cd "$REPO_ROOT/web" && nohup npm run dev -- --host 0.0.0.0 --port 5173 >"$FRONTEND_LOG" 2>&1 & echo $! >"$FRONTEND_PID_FILE")
  echo "Frontend running → $(cat "$FRONTEND_PID_FILE") (logs: $FRONTEND_LOG)"
}

run_backend
run_frontend

echo "Both services are up. Backend http://localhost:8000 , Frontend http://localhost:5173"
