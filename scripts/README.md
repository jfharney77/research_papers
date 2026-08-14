# Scripts

- `start_web.sh` / `stop_web.sh` — run the FastAPI backend + React frontend (see below).
- `build_apip_paper.sh` — compile the APIP paper in `papers/apip/` to PDF.

## Build the APIP paper

```bash
./scripts/build_apip_paper.sh          # Linux / macOS / WSL
```

```bat
scripts\build_apip_paper.bat           :: Windows cmd.exe
```

Runs `pdflatex → bibtex → pdflatex → pdflatex` in `papers/apip/` and writes
`papers/apip/main.pdf`, then reports the page count plus any undefined
references, undefined citations, or overfull boxes from `main.log`.

| Flag | Effect |
| --- | --- |
| `-c`, `--clean` | Delete `.aux/.bbl/.blg/.log/.out` before building — use after editing `references.bib` or renaming a `\label` |
| `-q`, `--quiet` | Hide pdflatex/bibtex chatter; print only the summary |
| `-s DIR`, `--src DIR` | Build a different paper directory instead of `papers/apip` |
| `-h`, `--help` | Usage text |

Both scripts take the same flags. `IEEEtran.cls` and `IEEEtran.bst` are
vendored in `papers/apip/`, so no IEEE TeX Live package is needed — only
`pdflatex` and `bibtex`.

On Linux, as with the `script/latex/*` build scripts, host auto-install is off
by default; set `LATEX_AUTO_INSTALL=1` to let the script `apt-get` TeX Live.
The `.bat` has no auto-install equivalent (that path is apt-specific) — install
[MiKTeX](https://miktex.org) or TeX Live for Windows first.

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
