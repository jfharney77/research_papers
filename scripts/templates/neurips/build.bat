@echo off
rem ==========================================================================
rem  build.bat -- Compile the NeurIPS template (templates\latex\neurips)
rem
rem  Windows batch equivalent of scripts/templates/neurips/build.sh. A thin
rem  wrapper over scripts\lib\latex_build.bat (flags: -c/--clean, -q/--quiet,
rem  -s/--src, -h/--help).
rem
rem  Style files: neurips_<year>.sty is downloaded from the NeurIPS site on
rem  first build (curl + PowerShell Expand-Archive, both standard on
rem  Windows 10+) and then version-controlled. Update STYLE_YEAR and
rem  STYLE_URL below each year; find the current link at
rem  https://neurips.cc/Conferences/<YEAR>/PaperInformation/StyleFiles
rem
rem  Note: the download check runs against the default source directory; if
rem  you build another directory with --src, place the .sty there yourself.
rem ==========================================================================
setlocal

rem --- Style file configuration -- update each year -------------------------
set "STYLE_YEAR=2025"
set "STYLE_URL=https://media.neurips.cc/Conferences/NeurIPS%STYLE_YEAR%/Styles.zip"

for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
set "LATEX_NAME=NeurIPS template"
set "LATEX_SRC=%REPO_ROOT%\templates\latex\neurips"

rem --- Download the NeurIPS style file if it is not already present ---------
if exist "%LATEX_SRC%\neurips_*.sty" goto style_ok

echo [INFO] NeurIPS style file not found. Attempting download ...

where curl >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl not found. Cannot auto-download the style file.
    echo         Download neurips_%STYLE_YEAR%.sty manually from:
    echo         https://neurips.cc/Conferences/%STYLE_YEAR%/PaperInformation/StyleFiles
    echo         and place it in: %LATEX_SRC%
    exit /b 1
)

set "ZIP_FILE=%LATEX_SRC%\neurips_%STYLE_YEAR%.zip"
set "UNPACK_DIR=%LATEX_SRC%\neurips_style_tmp"

echo [INFO] Downloading: %STYLE_URL%
curl -L --fail --show-error -o "%ZIP_FILE%" "%STYLE_URL%"
if errorlevel 1 (
    echo [ERROR] Download failed. Fetch the style file manually and place it
    echo         in: %LATEX_SRC%
    exit /b 1
)

echo [INFO] Extracting style file ...
powershell -NoProfile -Command "Expand-Archive -Force '%ZIP_FILE%' '%UNPACK_DIR%'; Get-ChildItem -Recurse '%UNPACK_DIR%' -Filter *.sty | Copy-Item -Destination '%LATEX_SRC%'"
if errorlevel 1 (
    echo [ERROR] Extraction failed. Unzip %ZIP_FILE% by hand and copy the
    echo         .sty file into: %LATEX_SRC%
    exit /b 1
)
rmdir /s /q "%UNPACK_DIR%" 2>nul
del /q "%ZIP_FILE%" 2>nul

if not exist "%LATEX_SRC%\neurips_*.sty" (
    echo [ERROR] Download completed but no neurips_*.sty appeared in %LATEX_SRC%
    exit /b 1
)
echo [INFO] Style file installed.

:style_ok
call "%~dp0..\..\lib\latex_build.bat" %*
exit /b %errorlevel%
