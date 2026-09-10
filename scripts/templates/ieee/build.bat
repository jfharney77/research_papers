@echo off
rem ==========================================================================
rem  build.bat -- Compile the IEEE conference template (templates\latex\ieee)
rem
rem  Windows batch equivalent of scripts/templates/ieee/build.sh. A thin
rem  wrapper over scripts\lib\latex_build.bat (flags: -c/--clean, -q/--quiet,
rem  -s/--src, -h/--help).
rem
rem  Requirements: pdflatex and bibtex on PATH (MiKTeX or TeX Live for
rem  Windows). MiKTeX installs the IEEEtran package on demand.
rem ==========================================================================
setlocal

for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
set "LATEX_NAME=IEEE template"
set "LATEX_SRC=%REPO_ROOT%\templates\latex\ieee"

call "%~dp0..\..\lib\latex_build.bat" %*
exit /b %errorlevel%
