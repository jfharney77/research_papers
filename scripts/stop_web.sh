#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "$LOG_DIR"
BACKEND_PID_FILE="${LOG_DIR}/.backend.pid"
FRONTEND_PID_FILE="${LOG_DIR}/.frontend.pid"

child_pids() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -P "$1" 2>/dev/null || true
  else
    echo ""
  fi
}

terminate_tree() {
  local signal=$1
  local pid=$2
  if [[ -z "$pid" ]]; then
    return
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return
  fi
  local kids
  kids="$(child_pids "$pid")"
  for kid in $kids; do
    terminate_tree "$signal" "$kid"
  done
  kill -"$signal" "$pid" >/dev/null 2>&1 || true
}

kill_port_listener() {
  local port=$1
  local label=$2
  local pids
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti ":${port}" 2>/dev/null | tr '\n' ' ')
  elif command -v fuser >/dev/null 2>&1; then
    pids=$(fuser "${port}/tcp" 2>/dev/null | tr '\n' ' ')
  else
    return
  fi
  for pid in $pids; do
    if [[ -n "$pid" ]]; then
      echo "${label}: forcing PID ${pid} off port ${port}";
      terminate_tree TERM "$pid"
      sleep 0.5
      if kill -0 "$pid" >/dev/null 2>&1; then
        terminate_tree KILL "$pid"
      fi
    fi
  done
}

stop_pid() {
  local name=$1
  local pid_file=$2
  if [[ ! -f "$pid_file" ]]; then
    echo "${name}: no pid file present, skipping."
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  if [[ -z "$pid" ]]; then
    echo "${name}: pid file empty, removing."
    rm -f "$pid_file"
    return
  fi
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Stopping ${name} (pid $pid)..."
    terminate_tree TERM "$pid"
    for _ in {1..10}; do
      if kill -0 "$pid" >/dev/null 2>&1; then
        sleep 0.5
      else
        break
      fi
    done
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "${name} did not exit in time; sending SIGKILL"
      terminate_tree KILL "$pid"
    fi
  else
    echo "${name}: process $pid not running, cleaning stale pid file."
  fi
  rm -f "$pid_file"
}

stop_pid "Backend" "$BACKEND_PID_FILE"
stop_pid "Frontend" "$FRONTEND_PID_FILE"

kill_port_listener 8000 "Backend"
kill_port_listener 5173 "Frontend"

echo "Services stopped."
