@echo off
rem ==========================================================================
rem  build.bat -- Compile the ACM conference template (templates\latex\acm)
rem
rem  Windows batch equivalent of scripts/templates/acm/build.sh. A thin
rem  wrapper over scripts\lib\latex_build.bat (flags: -c/--clean, -q/--quiet,
rem  -s/--src, -h/--help).
rem
rem  Style files: acmart.cls and the acm*.bbx/cbx/dbx files are
rem  version-controlled in templates\latex\acm\ (v2.03, Feb 2024). To update,
rem  replace them with newer versions from https://ctan.org/pkg/acmart
rem ==========================================================================
setlocal

for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
set "LATEX_NAME=ACM template"
set "LATEX_SRC=%REPO_ROOT%\templates\latex\acm"

if not exist "%LATEX_SRC%\acmart.cls" (
    echo [ERROR] Missing required file: %LATEX_SRC%\acmart.cls
    echo         Download the latest acmart from https://ctan.org/pkg/acmart and
    echo         place acmart.cls plus the acm*.bbx/cbx/dbx files in %LATEX_SRC%
    exit /b 1
)

call "%~dp0..\..\lib\latex_build.bat" %*
exit /b %errorlevel%
