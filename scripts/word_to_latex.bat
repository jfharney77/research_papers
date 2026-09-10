@echo off
rem ==========================================================================
rem  word_to_latex.bat -- Convert a paper's Word manuscript into per-section
rem  LaTeX (Windows)
rem
rem  Batch equivalent of scripts/word_to_latex.sh. Wraps the product converter
rem  (src\docbuilder) so it writes into a paper's own directory instead of the
rem  docserver's runtime workspace.
rem
rem  Usage:
rem      scripts\word_to_latex.bat                        (APIP, newest .docx)
rem      scripts\word_to_latex.bat <slug>                 (another paper)
rem      scripts\word_to_latex.bat --docx path\to\file.docx
rem
rem  Options:
rem      -d, --docx FILE   Manuscript to convert. Default: the most recently
rem                        modified .docx in papers\<slug>\manuscript\.
rem      -t, --template ID Conference template to convert against (default: ieee).
rem      -o, --out DIR     Where to write the result. Default:
rem                        papers\<slug>\latex.imported\
rem      -f, --force       Write straight into papers\<slug>\latex\, moving the
rem                        existing one aside to latex.bak-<timestamp>\ first.
rem      -h, --help, /?    Show this help text.
rem
rem  BY DEFAULT THIS DOES NOT TOUCH papers\<slug>\latex\. That directory holds
rem  hand-edited LaTeX. A fresh conversion is written alongside it so you can
rem  diff and merge deliberately. --force overwrites, keeping a timestamped
rem  backup.
rem
rem  Requires uv (https://docs.astral.sh/uv/) on PATH.
rem ==========================================================================
setlocal EnableDelayedExpansion

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"

set "SLUG=apip"
set "DOCX="
set "TEMPLATE=ieee"
set "OUT="
set "FORCE=0"

rem --- Parse arguments ------------------------------------------------------
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="-d"          goto set_docx
if /i "%~1"=="--docx"      goto set_docx
if /i "%~1"=="-t"          goto set_template
if /i "%~1"=="--template"  goto set_template
if /i "%~1"=="-o"          goto set_out
if /i "%~1"=="--out"       goto set_out
if /i "%~1"=="-f"          ( set "FORCE=1" & shift & goto parse_args )
if /i "%~1"=="--force"     ( set "FORCE=1" & shift & goto parse_args )
if /i "%~1"=="-h"          goto usage
if /i "%~1"=="--help"      goto usage
if /i "%~1"=="/?"          goto usage
set "ARG=%~1"
if "%ARG:~0,1%"=="-" (
    echo [ERROR] Unknown option: %~1
    echo         Run "%~nx0 --help" for usage.
    exit /b 2
)
set "SLUG=%~1"
shift
goto parse_args

:set_docx
if "%~2"=="" ( echo [ERROR] --docx requires a file & exit /b 2 )
set "DOCX=%~f2"
shift & shift
goto parse_args

:set_template
if "%~2"=="" ( echo [ERROR] --template requires an id & exit /b 2 )
set "TEMPLATE=%~2"
shift & shift
goto parse_args

:set_out
if "%~2"=="" ( echo [ERROR] --out requires a directory & exit /b 2 )
set "OUT=%~f2"
shift & shift
goto parse_args

:args_done

set "PAPER_DIR=%REPO_ROOT%\papers\%SLUG%"
if not exist "%PAPER_DIR%\" (
    echo [ERROR] No such paper: papers\%SLUG%
    echo         Look in %REPO_ROOT%\papers\ for the available ones.
    exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found. Install it from https://docs.astral.sh/uv/
    exit /b 1
)

rem --- Pick the manuscript --------------------------------------------------
if defined DOCX goto docx_chosen
set "MANUSCRIPT_DIR=%PAPER_DIR%\manuscript"
for /f "delims=" %%F in ('dir /b /o-d "%MANUSCRIPT_DIR%\*.docx" 2^>nul') do (
    if not defined DOCX set "DOCX=%MANUSCRIPT_DIR%\%%F"
)
if not defined DOCX (
    echo [ERROR] No .docx found in %MANUSCRIPT_DIR%
    echo         Pass one explicitly with --docx.
    exit /b 1
)
echo [INFO] Using newest manuscript: %DOCX%
echo        ^(override with --docx if you meant a different version^)

:docx_chosen
if not exist "%DOCX%" (
    echo [ERROR] No such file: %DOCX%
    exit /b 1
)

if not exist "%REPO_ROOT%\templates\latex\%TEMPLATE%\main.tex" (
    echo [ERROR] No such template: %TEMPLATE%
    echo         Look in %REPO_ROOT%\templates\latex\ for the available ones.
    exit /b 1
)

rem --- Run the converter ----------------------------------------------------
rem The converter writes into documents\<id>\ and refuses to clobber an
rem existing workspace, so clear any leftover from a previous run first.
rem documents\ is gitignored scratch space -- nothing there is precious.
for %%F in ("%DOCX%") do set "DOC_BASE=%%~nF"
for /f "delims=" %%A in ('powershell -NoProfile -Command "('%DOC_BASE%'.ToLower() -replace '[^a-z0-9]+','_').Trim('_')"') do set "DOC_ID=%%A"
set "WORKSPACE=%REPO_ROOT%\documents\%DOC_ID%"
if exist "%WORKSPACE%" rmdir /s /q "%WORKSPACE%"

echo [INFO] Converting with the %TEMPLATE% template ...
pushd "%REPO_ROOT%"
set "PYTHONPATH=src"
uv run python -m docbuilder.cli "%DOCX%" --template %TEMPLATE% --no-build
if errorlevel 1 ( popd & exit /b 1 )
popd

set "CONVERTED=%WORKSPACE%\%TEMPLATE%"
if not exist "%CONVERTED%\main.tex" (
    echo [ERROR] Converter produced no main.tex in %CONVERTED%
    exit /b 1
)

rem --- Place the result -----------------------------------------------------
if "%FORCE%"=="1" (
    set "DEST=%PAPER_DIR%\latex"
    if exist "!DEST!\" (
        for /f "delims=" %%A in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "TS=%%A"
        move "!DEST!" "%PAPER_DIR%\latex.bak-!TS!" >nul
        echo [INFO] Existing LaTeX moved to papers\%SLUG%\latex.bak-!TS!\
    )
) else (
    if defined OUT ( set "DEST=%OUT%" ) else ( set "DEST=%PAPER_DIR%\latex.imported" )
    if exist "!DEST!\" rmdir /s /q "!DEST!"
)

robocopy "%CONVERTED%" "!DEST!" /e >nul
if errorlevel 8 (
    echo [ERROR] Copying the converted LaTeX failed.
    exit /b 1
)

rem The converter copies the template directory wholesale, which on a working
rem checkout carries build artifacts from the last time it was built.
del /q "!DEST!\main.aux" "!DEST!\main.bbl" "!DEST!\main.blg" "!DEST!\main.log" "!DEST!\main.out" "!DEST!\main.pdf" "!DEST!\main.toc" "!DEST!\main.synctex.gz" 2>nul

echo.
echo ============================================================
echo  Converted: %DOCX%
echo  Output   : !DEST!\
echo ============================================================

if "%FORCE%"=="1" (
    echo.
    echo Build it:  scripts\papers\%SLUG%\build.bat
) else (
    echo.
    echo This did NOT modify papers\%SLUG%\latex\. Merge what you want by hand,
    echo or re-run with --force to replace papers\%SLUG%\latex\ ^(the old one is
    echo kept as latex.bak-^<timestamp^>\^).
)
exit /b 0

:usage
echo word_to_latex.bat -- Convert a paper's Word manuscript into per-section LaTeX
echo.
echo Usage:
echo     scripts\word_to_latex.bat [slug] [options]
echo.
echo Options:
echo     -d, --docx FILE   Manuscript to convert ^(default: newest .docx in
echo                       papers\^<slug^>\manuscript\^).
echo     -t, --template ID Conference template ^(default: ieee^).
echo     -o, --out DIR     Output directory ^(default: papers\^<slug^>\latex.imported\^).
echo     -f, --force       Write straight into papers\^<slug^>\latex\, backing up
echo                       the existing one to latex.bak-^<timestamp^>\ first.
echo     -h, --help, /?    Show this help text.
exit /b 0
