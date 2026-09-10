@echo off
rem ==========================================================================
rem  new-paper.bat -- Scaffold a new paper (Windows)
rem
rem  Batch equivalent of scripts/new-paper.sh, so papers\ and scripts\papers\
rem  stay in sync.
rem
rem  Usage:
rem      scripts\new-paper.bat <slug> [conference]
rem
rem      <slug>        Directory name for the paper, e.g. "agent-drift".
rem                    Lowercase letters, digits, hyphens, underscores only.
rem      [conference]  Template to seed papers\<slug>\latex from. One of the
rem                    directories in templates\latex\ (default: ieee).
rem
rem  Creates:
rem      papers\<slug>\manuscript\     .docx / .md source material
rem      papers\<slug>\latex\          main.tex + sections\, copied from the template
rem      papers\<slug>\figures\
rem      papers\<slug>\deck\
rem      scripts\papers\<slug>\build.sh   (bash wrapper over lib/latex_build.sh)
rem      scripts\papers\<slug>\build.bat  (batch wrapper over lib\latex_build.bat)
rem ==========================================================================
setlocal

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"

set "SLUG=%~1"
set "CONFERENCE=%~2"
if "%CONFERENCE%"=="" set "CONFERENCE=ieee"

if "%SLUG%"=="" (
    echo Usage: scripts\new-paper.bat ^<slug^> [conference]
    echo        Run with a slug, e.g.: scripts\new-paper.bat agent-drift ieee
    exit /b 2
)

rem findstr ranges match case-insensitively, so use PowerShell's -cmatch for a
rem genuinely case-sensitive check.
powershell -NoProfile -Command "exit [int](-not ('%SLUG%' -cmatch '^[a-z0-9_-]+$'))" || (
    echo [ERROR] Invalid slug: %SLUG%
    echo         Use lowercase letters, digits, hyphens and underscores only.
    exit /b 2
)

set "TEMPLATE_DIR=%REPO_ROOT%\templates\latex\%CONFERENCE%"
set "PAPER_DIR=%REPO_ROOT%\papers\%SLUG%"
set "SCRIPT_DIR=%REPO_ROOT%\scripts\papers\%SLUG%"

if not exist "%TEMPLATE_DIR%\main.tex" (
    echo [ERROR] No such template: %CONFERENCE%
    echo         Look in %REPO_ROOT%\templates\latex\ for the available ones.
    exit /b 1
)

if exist "%PAPER_DIR%" (
    echo [ERROR] papers\%SLUG% already exists.
    exit /b 1
)

echo [INFO] Creating papers\%SLUG% from the %CONFERENCE% template ...
mkdir "%PAPER_DIR%\manuscript" "%PAPER_DIR%\figures" "%PAPER_DIR%\deck" "%PAPER_DIR%\latex"

rem Copy the template skeleton, leaving build artifacts behind.
rem robocopy exit codes 0-7 mean success; 8+ is a real failure.
robocopy "%TEMPLATE_DIR%" "%PAPER_DIR%\latex" /e /xf main.aux main.bbl main.blg main.log main.out main.pdf main.toc main.synctex.gz >nul
if errorlevel 8 (
    echo [ERROR] Copying the template failed.
    exit /b 1
)

echo [INFO] Creating scripts\papers\%SLUG%\build.sh and build.bat ...
mkdir "%SCRIPT_DIR%"

set "SH=%SCRIPT_DIR%\build.sh"
echo #!/usr/bin/env bash> "%SH%"
echo # =============================================================================>> "%SH%"
echo # build.sh -- Compile the %SLUG% paper (papers/%SLUG%/latex) to PDF>> "%SH%"
echo #>> "%SH%"
echo # Usage:>> "%SH%"
echo #   bash scripts/papers/%SLUG%/build.sh [-c^|--clean] [-q^|--quiet] [-s^|--src DIR]>> "%SH%"
echo #>> "%SH%"
echo # Seeded from the %CONFERENCE% template. Host TeX Live auto-install is disabled>> "%SH%"
echo # by default; set LATEX_AUTO_INSTALL=1 to allow it.>> "%SH%"
echo # =============================================================================>> "%SH%"
echo set -euo pipefail>> "%SH%"
echo source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" ^&^& pwd)/latex_build.sh">> "%SH%"
echo.>> "%SH%"
echo LATEX_NAME="%SLUG% paper">> "%SH%"
echo LATEX_SRC="${REPO_ROOT}/papers/%SLUG%/latex">> "%SH%"
echo.>> "%SH%"
echo latex_parse_args "$@">> "%SH%"
echo require_texlive>> "%SH%"
echo latex_build>> "%SH%"

set "BAT=%SCRIPT_DIR%\build.bat"
echo @echo off> "%BAT%"
echo rem build.bat -- Compile the %SLUG% paper (papers\%SLUG%\latex) to PDF>> "%BAT%"
echo rem Seeded from the %CONFERENCE% template. Thin wrapper over scripts\lib\latex_build.bat.>> "%BAT%"
echo setlocal>> "%BAT%"
echo for %%%%I in ("%%~dp0..\..\..") do set "REPO_ROOT=%%%%~fI">> "%BAT%"
echo set "LATEX_NAME=%SLUG% paper">> "%BAT%"
echo set "LATEX_SRC=%%REPO_ROOT%%\papers\%SLUG%\latex">> "%BAT%"
echo call "%%~dp0..\..\lib\latex_build.bat" %%*>> "%BAT%"
echo exit /b %%errorlevel%%>> "%BAT%"

rem Keep the empty content dirs in git.
type nul > "%PAPER_DIR%\manuscript\.gitkeep"
type nul > "%PAPER_DIR%\figures\.gitkeep"
type nul > "%PAPER_DIR%\deck\.gitkeep"

echo.
echo Created:
echo   papers\%SLUG%\{manuscript,latex,figures,deck}\
echo   scripts\papers\%SLUG%\build.sh
echo   scripts\papers\%SLUG%\build.bat
echo.
echo Next: drop your .docx in papers\%SLUG%\manuscript\, then run
echo   scripts\papers\%SLUG%\build.bat
exit /b 0
