@echo off
REM =============================================================================
REM build.bat -- Compile IEEE LaTeX document to PDF
REM
REM Usage:
REM   From any directory:
REM     script\latex\ieee\build.bat
REM
REM   Or from within script\latex\ieee\:
REM     build.bat
REM
REM The script must be run from the repository root, OR you can pass the
REM path to the ieee latex directory as the first argument:
REM
REM   build.bat [path\to\latex\ieee]
REM
REM Requirements:
REM   - A LaTeX distribution in your PATH (TeX Live or MiKTeX recommended)
REM     Commands used: pdflatex, bibtex
REM =============================================================================

setlocal EnableDelayedExpansion

REM --- Resolve the latex/ieee source directory ---
if "%~1"=="" (
    REM Default: assume script is run from repository root
    set "SRC_DIR=%~dp0..\..\..\latex\ieee"
) else (
    set "SRC_DIR=%~1"
)

REM Normalise the path (removes trailing backslash, resolves ..)
for %%D in ("%SRC_DIR%") do set "SRC_DIR=%%~fD"

REM --- Validate source directory ---
if not exist "%SRC_DIR%\main.tex" (
    echo [ERROR] Cannot find main.tex in: %SRC_DIR%
    echo         Run this script from the repository root, or pass the
    echo         path to the latex\ieee directory as an argument.
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
echo  Building IEEE LaTeX document
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
