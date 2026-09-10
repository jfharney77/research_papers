@echo off
rem ==========================================================================
rem  build.bat -- Compile the APIP paper (papers\apip\latex) to PDF
rem
rem  Windows batch equivalent of scripts/papers/apip/build.sh. A thin wrapper
rem  over scripts\lib\latex_build.bat, which supplies the flags (-c/--clean,
rem  -q/--quiet, -s/--src, -h/--help) and the four-pass build.
rem
rem  Usage (from anywhere -- paths resolve relative to this script):
rem      scripts\papers\apip\build.bat [options]
rem
rem  IEEEtran.cls and IEEEtran.bst are vendored in papers\apip\latex\, so no
rem  IEEE MiKTeX/TeX Live package is required -- only pdflatex and bibtex.
rem ==========================================================================
setlocal

for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
set "LATEX_NAME=APIP paper"
set "LATEX_SRC=%REPO_ROOT%\papers\apip\latex"

call "%~dp0..\..\lib\latex_build.bat" %*
exit /b %errorlevel%
