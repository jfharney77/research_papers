@echo off
REM =============================================================================
REM build.bat -- Compile ACM LaTeX document to PDF
REM
REM Usage:
REM   From any directory:
REM     script\latex\acm\build.bat
REM
REM   Or from within script\latex\acm\:
REM     build.bat
REM
REM   Pass the path to the acm latex directory as the first argument:
REM     build.bat [path\to\latex\acm]
REM
REM Requirements:
REM   - A LaTeX distribution in your PATH (TeX Live or MiKTeX recommended)
REM     Commands used: pdflatex, bibtex
REM   - acmart.cls -- committed locally in latex\acm\ (v2.03, Feb 2024)
REM     To update: replace acmart.cls and the acm*.bbx/cbx/dbx files in latex\acm\
REM     with newer versions from https://ctan.org/pkg/acmart
REM =============================================================================

setlocal EnableDelayedExpansion

REM --- Resolve the latex/acm source directory ---
if "%~1"=="" (
    REM Default: assume script is run from repository root
    set "SRC_DIR=%~dp0..\..\..\latex\acm"
) else (
    set "SRC_DIR=%~1"
)

REM Normalise the path (removes trailing backslash, resolves ..)
for %%D in ("%SRC_DIR%") do set "SRC_DIR=%%~fD"

REM --- Validate source directory ---
if not exist "%SRC_DIR%\main.tex" (
    echo [ERROR] Cannot find main.tex in: %SRC_DIR%
    echo         Run this script from the repository root, or pass the
    echo         path to the latex\acm directory as an argument.
    exit /b 1
)

REM --- Check that acmart.cls is present ---
if not exist "%SRC_DIR%\acmart.cls" (
    echo [ERROR] acmart.cls not found in: %SRC_DIR%
    echo         Download the latest version from: https://ctan.org/pkg/acmart
    echo         and place acmart.cls and the acm*.bbx/cbx/dbx files in: %SRC_DIR%
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

REM --- Build ---
echo.
echo ============================================================
echo  Building ACM LaTeX document
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
