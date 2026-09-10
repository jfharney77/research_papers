@echo off
rem ==========================================================================
rem  run_sim.bat -- Launch the APIP simulation (Windows)
rem
rem  Batch equivalent of scripts/papers/apip/run_sim.sh. Launches the APIP
rem  simulation that backs the paper's case study (a separate app from the
rem  Word-to-LaTeX product). Runs from the repo root so the package resolves;
rem  uses port 8100 so it never collides with the product server on :8000.
rem
rem  Requires uv (https://docs.astral.sh/uv/) on PATH.
rem ==========================================================================
setlocal

for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
cd /d "%REPO_ROOT%"

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found. Install it from https://docs.astral.sh/uv/
    exit /b 1
)

echo Installing dependencies...
uv sync
if errorlevel 1 exit /b 1

echo Starting APIP simulation server on :8100 ...
uv run uvicorn sims.apip_sim.backend.main:app --reload --host 0.0.0.0 --port 8100
exit /b %errorlevel%
