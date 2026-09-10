@echo off
rem ==========================================================================
rem  build.bat -- Compile the AAAI conference template (templates\latex\aaai)
rem
rem  Windows batch equivalent of scripts/templates/aaai/build.sh. A thin
rem  wrapper over scripts\lib\latex_build.bat (flags: -c/--clean, -q/--quiet,
rem  -s/--src, -h/--help).
rem
rem  Style files: aaai2026.sty and aaai2026.bst are version-controlled in
rem  templates\latex\aaai\. To update for a new year, download the author kit
rem  from the AAAI site, replace both files, and bump STYLE_YEAR below.
rem
rem  This template always cleans auxiliary files first -- a stale main.aux
rem  triggers duplicate \bibstyle errors under aaai2026.bst.
rem ==========================================================================
setlocal

set "STYLE_YEAR=2026"

for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
set "LATEX_NAME=AAAI template"
set "LATEX_SRC=%REPO_ROOT%\templates\latex\aaai"
set "LATEX_ALWAYS_CLEAN=1"

if not exist "%LATEX_SRC%\aaai%STYLE_YEAR%.sty" (
    echo [ERROR] Missing required file: %LATEX_SRC%\aaai%STYLE_YEAR%.sty
    echo         Download the AAAI author kit from
    echo         https://aaai.org/conference/aaai/aaai-%STYLE_YEAR%/aaai-%STYLE_YEAR%-author-kit/
    echo         and extract aaai%STYLE_YEAR%.sty and aaai%STYLE_YEAR%.bst into %LATEX_SRC%
    exit /b 1
)

call "%~dp0..\..\lib\latex_build.bat" %*
exit /b %errorlevel%
