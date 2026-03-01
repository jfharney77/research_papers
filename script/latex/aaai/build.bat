@echo off
REM =============================================================================
REM build.bat -- Compile AAAI LaTeX document to PDF
REM
REM Usage:
REM   From any directory:
REM     script\latex\aaai\build.bat
REM
REM   Or from within script\latex\aaai\:
REM     build.bat
REM
REM   Pass the path to the aaai latex directory as the first argument:
REM     build.bat [path\to\latex\aaai]
REM
REM Requirements:
REM   - A LaTeX distribution in your PATH (TeX Live or MiKTeX recommended)
REM     Commands used: pdflatex, bibtex
REM
REM Style files:
REM   aaai2026.sty and aaai2026.bst are extracted from the author kit zip
REM   bundled in this repository at style_kits\AAAI\.
REM   To update for a new year, place the new AuthorKitYY.zip in style_kits\AAAI\
REM   and update STYLE_YEAR and STY_FILE below.
REM =============================================================================

setlocal EnableDelayedExpansion

REM =============================================================================
REM STYLE FILE CONFIGURATION -- update each year
REM =============================================================================
set "STYLE_YEAR=2026"
set "STY_FILE=aaai2026.sty"
set "BST_FILE=aaai2026.bst"
set "KIT_SUBDIR=AuthorKit26/AnonymousSubmission/LaTeX"
REM =============================================================================

REM --- Resolve paths ---
REM Script lives at script\latex\aaai\ so three levels up is the repo root
set "REPO_ROOT=%~dp0..\..\..\"
for %%D in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fD"

if "%~1"=="" (
    set "SRC_DIR=%REPO_ROOT%latex\aaai"
) else (
    set "SRC_DIR=%~1"
)
for %%D in ("%SRC_DIR%") do set "SRC_DIR=%%~fD"

REM --- Validate source directory ---
if not exist "%SRC_DIR%\main.tex" (
    echo [ERROR] Cannot find main.tex in: %SRC_DIR%
    echo         Run this script from the repository root, or pass the
    echo         path to the latex\aaai directory as an argument.
    exit /b 1
)

REM --- Check that AAAI style files are present ---
if not exist "%SRC_DIR%\%STY_FILE%" (
    echo [ERROR] %STY_FILE% not found in: %SRC_DIR%
    echo         Download the AAAI author kit from:
    echo         https://aaai.org/conference/aaai/aaai-20%STYLE_YEAR:~2,2%/aaai-20%STYLE_YEAR:~2,2%-author-kit/
    echo         and extract %STY_FILE% and %BST_FILE% into: %SRC_DIR%
    exit /b 1
)

REM --- Check that pdflatex and bibtex are available ---
where pdflatex >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pdflatex not found. Install TeX Live or MiKTeX and ensure
    echo         it is added to your PATH.
    exit /b 1
)

where bibtex >nul 2>&1
if errorlevel 1 (
    echo [ERROR] bibtex not found. Install TeX Live or MiKTeX and ensure
    echo         it is added to your PATH.
    exit /b 1
)

REM --- Clean stale auxiliary files to prevent duplicate \bibstyle errors ---
echo [0/4] Cleaning auxiliary files ...
for %%E in (aux bbl blg lof lot toc out) do (
    if exist "%SRC_DIR%\main.%%E" del "%SRC_DIR%\main.%%E"
)

REM --- Build ---
echo.
echo ============================================================
echo  Building AAAI LaTeX document
echo  Source : %SRC_DIR%
echo ============================================================
echo.

pushd "%SRC_DIR%"

echo [1/4] pdflatex (first pass) ...
pdflatex -interaction=nonstopmode main.tex
if errorlevel 1 goto :latex_error

echo.
echo [2/4] bibtex (bibliography) ...
bibtex main
if errorlevel 1 goto :bibtex_error

echo.
echo [3/4] pdflatex (second pass -- resolving citations) ...
pdflatex -interaction=nonstopmode main.tex
if errorlevel 1 goto :latex_error

echo.
echo [4/4] pdflatex (third pass -- resolving cross-references) ...
pdflatex -interaction=nonstopmode main.tex
if errorlevel 1 goto :latex_error

popd

echo.
echo ============================================================
echo  Build complete!
echo  Output : %SRC_DIR%\main.pdf
echo ============================================================
echo.
exit /b 0

:latex_error
popd
echo.
echo [ERROR] pdflatex failed. Check the log at: %SRC_DIR%\main.log
exit /b 1

:bibtex_error
popd
echo.
echo [ERROR] bibtex failed. Check the log at: %SRC_DIR%\main.blg
exit /b 1
