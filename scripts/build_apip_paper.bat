@echo off
rem ==========================================================================
rem  build_apip_paper.bat -- Compile the APIP paper (papers\apip) to PDF
rem
rem  Windows batch equivalent of scripts/build_apip_paper.sh.
rem
rem  The paper is "Your Agent is Underperforming: The Case for Agent
rem  Performance Improvement Plans", converted from
rem  research\apip\APIP_Paper_v8_tracked.docx into the IEEE conference style
rem  from ieee_agc\.
rem
rem  Usage (from anywhere -- paths resolve relative to this script):
rem      scripts\build_apip_paper.bat
rem
rem  Options:
rem      -c, --clean       Delete .aux/.bbl/.blg/.log/.out before building
rem      -q, --quiet       Suppress pdflatex/bibtex output; summary only
rem      -s, --src DIR     Build a different paper directory
rem      -h, --help, /?    Show usage
rem
rem  Requirements:
rem      pdflatex and bibtex on PATH -- install MiKTeX (https://miktex.org)
rem      or TeX Live for Windows (https://tug.org/texlive). There is no
rem      auto-install path on Windows; the LATEX_AUTO_INSTALL escape hatch in
rem      the shell script is Debian/apt-specific and has no equivalent here.
rem
rem      IEEEtran.cls and IEEEtran.bst are vendored in papers\apip\, so no
rem      IEEE TeX Live/MiKTeX package is required.
rem ==========================================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
rem Normalise "...\scripts\.." to a clean absolute repo root.
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
set "SRC_DIR=%REPO_ROOT%\papers\apip"
set "CLEAN=0"
set "QUIET=0"

rem --- Parse arguments ------------------------------------------------------
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="-c"        ( set "CLEAN=1" & shift & goto parse_args )
if /i "%~1"=="--clean"   ( set "CLEAN=1" & shift & goto parse_args )
if /i "%~1"=="-q"        ( set "QUIET=1" & shift & goto parse_args )
if /i "%~1"=="--quiet"   ( set "QUIET=1" & shift & goto parse_args )
if /i "%~1"=="-s"        goto set_src
if /i "%~1"=="--src"     goto set_src
if /i "%~1"=="-h"        goto usage
if /i "%~1"=="--help"    goto usage
if /i "%~1"=="/?"        goto usage
echo [ERROR] Unknown argument: %~1
echo         Run "%~nx0 --help" for usage.
exit /b 2

:set_src
if "%~2"=="" (
    echo [ERROR] --src requires a directory
    exit /b 2
)
set "SRC_DIR=%~f2"
shift
shift
goto parse_args

:args_done

rem --- Validate source directory --------------------------------------------
if not exist "%SRC_DIR%\main.tex" (
    echo [ERROR] Cannot find main.tex in: %SRC_DIR%
    echo         Expected the APIP paper at papers\apip\, or pass another
    echo         directory with --src.
    exit /b 1
)

rem --- Check for pdflatex / bibtex ------------------------------------------
set "MISSING="
where pdflatex >nul 2>&1 || set "MISSING=!MISSING! pdflatex"
where bibtex   >nul 2>&1 || set "MISSING=!MISSING! bibtex"

if not "!MISSING!"=="" (
    echo [ERROR] Missing commands:!MISSING!
    echo         Install MiKTeX ^(https://miktex.org^) or TeX Live for Windows
    echo         ^(https://tug.org/texlive^) and make sure pdflatex and bibtex
    echo         are on your PATH, then re-run this script.
    exit /b 1
)

rem --- Build ----------------------------------------------------------------
echo.
echo ============================================================
echo  Building the APIP paper
echo  Source : %SRC_DIR%
echo ============================================================
echo.

pushd "%SRC_DIR%" || (
    echo [ERROR] Could not enter: %SRC_DIR%
    exit /b 1
)

if "%CLEAN%"=="1" (
    echo [0/4] cleaning auxiliary files ...
    del /q main.aux main.bbl main.blg main.log main.out main.toc main.synctex.gz 2>nul
)

echo [1/4] pdflatex ^(first pass^) ...
call :run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex
if errorlevel 1 goto build_failed

echo.
echo [2/4] bibtex ^(bibliography^) ...
call :run bibtex main
if errorlevel 1 goto build_failed

echo.
echo [3/4] pdflatex ^(second pass -- resolving citations^) ...
call :run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex
if errorlevel 1 goto build_failed

echo.
echo [4/4] pdflatex ^(third pass -- resolving cross-references^) ...
call :run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex
if errorlevel 1 goto build_failed

rem --- Report page count and warnings worth acting on ------------------------
set "PAGES="
for /f "tokens=5 delims=( " %%a in ('findstr /c:"Output written on main.pdf" main.log 2^>nul') do set "PAGES=%%a"

set "HAS_WARNINGS=0"
findstr /c:"Undefined control sequence" /c:"LaTeX Warning: Reference" /c:"LaTeX Warning: Citation" /c:"Overfull" main.log >nul 2>&1 && set "HAS_WARNINGS=1"

popd

echo.
echo ============================================================
echo  Build complete!
if defined PAGES (
    echo  Output : %SRC_DIR%\main.pdf  ^(%PAGES% pages^)
) else (
    echo  Output : %SRC_DIR%\main.pdf
)
if "%HAS_WARNINGS%"=="1" (
    echo ------------------------------------------------------------
    echo  Warnings ^(see %SRC_DIR%\main.log for detail^):
    findstr /c:"Undefined control sequence" /c:"LaTeX Warning: Reference" /c:"LaTeX Warning: Citation" /c:"Overfull" "%SRC_DIR%\main.log"
)
echo ============================================================
echo.
exit /b 0

rem --- Subroutines ----------------------------------------------------------

:run
rem Run a command, silencing its output when --quiet was passed.
if "%QUIET%"=="1" (
    %* >nul
) else (
    %*
)
exit /b %errorlevel%

:build_failed
popd
echo.
echo [ERROR] Build failed. See %SRC_DIR%\main.log for the LaTeX error.
exit /b 1

:usage
echo build_apip_paper.bat -- Compile the APIP paper ^(papers\apip^) to PDF
echo.
echo Usage:
echo     scripts\build_apip_paper.bat [options]
echo.
echo Options:
echo     -c, --clean       Delete .aux/.bbl/.blg/.log/.out before building.
echo                       Use after editing references.bib or renaming a
echo                       label, when stale aux files cause spurious
echo                       "undefined reference" warnings.
echo     -q, --quiet       Suppress pdflatex/bibtex output; summary only.
echo     -s, --src DIR     Build a different paper directory
echo                       ^(default: papers\apip^).
echo     -h, --help, /?    Show this help text.
echo.
echo Requirements:
echo     pdflatex and bibtex on PATH ^(MiKTeX or TeX Live for Windows^).
echo     IEEEtran.cls and IEEEtran.bst are vendored in papers\apip\, so no
echo     IEEE TeX package is required.
exit /b 0
