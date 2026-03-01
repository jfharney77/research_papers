@echo off
REM =============================================================================
REM build.bat -- Compile NeurIPS LaTeX document to PDF
REM
REM Usage:
REM   From any directory:
REM     script\latex\neurips\build.bat
REM
REM   Or from within script\latex\neurips\:
REM     build.bat
REM
REM   Pass the path to the neurips latex directory as the first argument:
REM     build.bat [path\to\latex\neurips]
REM
REM Requirements:
REM   - A LaTeX distribution in your PATH (TeX Live or MiKTeX recommended)
REM     Commands used: pdflatex, bibtex
REM   - curl in your PATH (included in Windows 10 1803+ by default)
REM =============================================================================

setlocal EnableDelayedExpansion

REM =============================================================================
REM STYLE FILE CONFIGURATION
REM Update STYLE_YEAR and STYLE_URL each year when NeurIPS releases new files.
REM Find the latest download link at:
REM   https://neurips.cc/Conferences/<YEAR>/PaperInformation/StyleFiles
REM =============================================================================
set "STYLE_YEAR=2025"
set "STYLE_URL=https://media.nips.cc/Conferences/2025/Styles/neurips_2025.zip"
REM =============================================================================

REM --- Resolve the latex/neurips source directory ---
if "%~1"=="" (
    REM Default: assume script is run from repository root
    set "SRC_DIR=%~dp0..\..\..\latex\neurips"
) else (
    set "SRC_DIR=%~1"
)

REM Normalise the path (removes trailing backslash, resolves ..)
for %%D in ("%SRC_DIR%") do set "SRC_DIR=%%~fD"

REM --- Validate source directory ---
if not exist "%SRC_DIR%\main.tex" (
    echo [ERROR] Cannot find main.tex in: %SRC_DIR%
    echo         Run this script from the repository root, or pass the
    echo         path to the latex\neurips directory as an argument.
    exit /b 1
)

REM --- Download NeurIPS style file if not already present ---
set "STY_FOUND=0"
for %%F in ("%SRC_DIR%\neurips_*.sty") do set "STY_FOUND=1"

if "%STY_FOUND%"=="0" (
    echo [INFO] NeurIPS style file not found. Attempting download ...

    where curl >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] curl not found. Cannot auto-download the style file.
        echo         Install curl or manually download neurips_%STYLE_YEAR%.sty from:
        echo         https://neurips.cc/Conferences/%STYLE_YEAR%/PaperInformation/StyleFiles
        echo         and place it in: %SRC_DIR%
        exit /b 1
    )

    set "ZIP_FILE=%SRC_DIR%\neurips_%STYLE_YEAR%.zip"

    echo [INFO] Downloading: %STYLE_URL%
    curl -L --fail --show-error -o "!ZIP_FILE!" "%STYLE_URL%"
    if errorlevel 1 (
        echo [ERROR] Download failed. The URL may have changed for this year.
        echo         Visit: https://neurips.cc/Conferences/%STYLE_YEAR%/PaperInformation/StyleFiles
        echo         to find the current download link and update STYLE_URL in this script.
        exit /b 1
    )

    echo [INFO] Extracting style file ...
    tar -xf "!ZIP_FILE!" -C "%SRC_DIR%" --wildcards "*.sty" 2>nul
    if errorlevel 1 (
        REM tar may not support --wildcards on all Windows versions; try without
        tar -xf "!ZIP_FILE!" -C "%SRC_DIR%"
    )
    del "!ZIP_FILE!"

    REM Verify extraction succeeded
    set "STY_FOUND=0"
    for %%F in ("%SRC_DIR%\neurips_*.sty") do set "STY_FOUND=1"
    if "!STY_FOUND!"=="0" (
        echo [ERROR] Extraction completed but neurips_*.sty not found in: %SRC_DIR%
        echo         Try downloading manually from:
        echo         https://neurips.cc/Conferences/%STYLE_YEAR%/PaperInformation/StyleFiles
        exit /b 1
    )

    echo [INFO] Style file downloaded successfully.
    echo.
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
echo  Building NeurIPS LaTeX document
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
