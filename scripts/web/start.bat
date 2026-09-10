@echo off
rem ==========================================================================
rem  start.bat -- Start the product backend + frontend (Windows)
rem
rem  Batch equivalent of scripts/web/start.sh. Starts the FastAPI backend on
rem  :8000 and the Vite frontend on :5173 as background processes, logging to
rem  logs\backend.log and logs\frontend.log. Stop them with scripts\web\stop.bat.
rem
rem  Instead of pid files, this checks whether the ports are already in use --
rem  more reliable on Windows, where the pid of a "start" child is awkward to
rem  capture from batch.
rem
rem  Requires: uv (or python with uvicorn installed) and npm on PATH.
rem ==========================================================================
setlocal

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "LOG_DIR=%REPO_ROOT%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

rem --- Refuse to double-start ------------------------------------------------
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul 2>&1 && (
    echo Backend already running ^(port 8000 is in use^). Stop it before starting a new session.
    exit /b 1
)
netstat -ano | findstr /r /c:":5173 .*LISTENING" >nul 2>&1 && (
    echo Frontend already running ^(port 5173 is in use^). Stop it before starting a new session.
    exit /b 1
)

rem --- Backend ---------------------------------------------------------------
set "BACKEND_CMD=uv run uvicorn docserver.main:app --host 0.0.0.0 --port 8000"
where uv >nul 2>&1 || set "BACKEND_CMD=python -m uvicorn docserver.main:app --host 0.0.0.0 --port 8000"

start "docserver-backend" /min cmd /c "cd /d "%REPO_ROOT%" && set PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH% && %BACKEND_CMD% > "%LOG_DIR%\backend.log" 2>&1"
echo Backend starting  (logs: %LOG_DIR%\backend.log)

rem --- Frontend --------------------------------------------------------------
start "docserver-frontend" /min cmd /c "cd /d "%REPO_ROOT%\web" && npm run dev -- --host 0.0.0.0 --port 5173 > "%LOG_DIR%\frontend.log" 2>&1"
echo Frontend starting (logs: %LOG_DIR%\frontend.log)

echo.
echo Both services are up. Backend http://localhost:8000 , Frontend http://localhost:5173
echo Stop them with: scripts\web\stop.bat
exit /b 0
