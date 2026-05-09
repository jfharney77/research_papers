# Web Stack Runbook

These helper scripts start/stop the FastAPI backend (`docserver`) and React frontend (`web/`).

## Prerequisites

- Python 3.12 environment with `uv` (preferred) or `python` + dependencies installed via `uv sync`/`pip install -r requirements`.
- Node.js + npm (for the Vite dev server) already bootstrapped in `web/` (`npm install`).
- Ports `8000` (backend) and `5173` (frontend) available locally.

## Start both services

```bash
./scripts/start_web.sh
```

What it does:

1. Ensures no existing PID files are running.
2. Launches `uvicorn docserver.main:app --port 8000` with `PYTHONPATH=src` so FastAPI can import the new modules.
3. Launches `npm run dev -- --host 0.0.0.0 --port 5173` inside `web/`.
4. Writes logs to `logs/backend.log` and `logs/frontend.log`; PIDs stored under `logs/.backend.pid` and `logs/.frontend.pid`.

## Stop both services

```bash
./scripts/stop_web.sh
```

The stop script:

- Reads each PID file, sends `SIGTERM`, waits up to ~5 seconds, and escalates to `SIGKILL` if needed.
- Cleans up PID files whether or not processes are running.

## Troubleshooting

- **“Failed to fetch” in the UI:** confirm the backend started successfully (`tail -f logs/backend.log`). If the backend crashed because it could not import modules, ensure you ran `./scripts/start_web.sh` (ensures backend imports via `PYTHONPATH=src`).
- Frontend dev server listens on `5173` with `VITE_API_BASE` pointing at `http://localhost:8000`.
- Use the UI’s “Delete” button or call `DELETE /documents/{id}` if a workspace needs to be removed.
- **Ports already in use:** stop other processes on 8000/5173 or edit the scripts to use alternate ports (keeping frontend `VITE_API_BASE` in sync).
- **Permission denied:** run `chmod +x scripts/start_web.sh scripts/stop_web.sh` once.
