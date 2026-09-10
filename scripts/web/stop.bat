@echo off
rem ==========================================================================
rem  stop.bat -- Stop the product backend + frontend (Windows)
rem
rem  Batch equivalent of scripts/web/stop.sh. Finds whatever is listening on
rem  ports 8000 (backend) and 5173 (frontend) and terminates it, child
rem  processes included (taskkill /T).
rem ==========================================================================
setlocal EnableDelayedExpansion

call :kill_port 8000 Backend
call :kill_port 5173 Frontend

echo Services stopped.
exit /b 0

:kill_port
set "PORT=%~1"
set "LABEL=%~2"
set "FOUND=0"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do (
    if not "%%p"=="0" (
        set "FOUND=1"
        echo %LABEL%: stopping PID %%p on port %PORT% ...
        taskkill /pid %%p /t /f >nul 2>&1
    )
)
if "!FOUND!"=="0" echo %LABEL%: nothing listening on port %PORT%, skipping.
exit /b 0
