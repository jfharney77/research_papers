@echo off
rem ==========================================================================
rem  to_output.bat -- Copy a built paper PDF into a shared output folder
rem  (Windows)
rem
rem  Batch equivalent of scripts/to_windows.sh. That script exists because WSL
rem  builds land on the Linux filesystem; on native Windows the PDF is already
rem  reachable, so this version just collects built PDFs into one folder
rem  (default: %USERPROFILE%\paper_output, override with PAPER_OUTPUT_DIR)
rem  so several papers can live side by side.
rem
rem  Usage:
rem      scripts\to_output.bat                 (copy the APIP paper)
rem      scripts\to_output.bat <slug>          (copy another paper)
rem      scripts\to_output.bat <slug> --build  (build it first, then copy)
rem
rem  Options:
rem      -b, --build       Run scripts\papers\<slug>\build.bat before copying.
rem      -d, --dest DIR    Destination directory.
rem      -o, --open        Open the copied PDF in the default viewer.
rem      -h, --help, /?    Show this help text.
rem
rem  The copy is named <slug>.pdf, not main.pdf, so several papers can live in
rem  the output folder without clobbering each other.
rem ==========================================================================
setlocal

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
if not defined PAPER_OUTPUT_DIR set "PAPER_OUTPUT_DIR=%USERPROFILE%\paper_output"
set "DEST_DIR=%PAPER_OUTPUT_DIR%"

set "SLUG=apip"
set "BUILD=0"
set "OPEN=0"

rem --- Parse arguments ------------------------------------------------------
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="-b"        ( set "BUILD=1" & shift & goto parse_args )
if /i "%~1"=="--build"   ( set "BUILD=1" & shift & goto parse_args )
if /i "%~1"=="-o"        ( set "OPEN=1" & shift & goto parse_args )
if /i "%~1"=="--open"    ( set "OPEN=1" & shift & goto parse_args )
if /i "%~1"=="-d"        goto set_dest
if /i "%~1"=="--dest"    goto set_dest
if /i "%~1"=="-h"        goto usage
if /i "%~1"=="--help"    goto usage
if /i "%~1"=="/?"        goto usage
set "ARG=%~1"
if "%ARG:~0,1%"=="-" (
    echo [ERROR] Unknown option: %~1
    echo         Run "%~nx0 --help" for usage.
    exit /b 2
)
set "SLUG=%~1"
shift
goto parse_args

:set_dest
if "%~2"=="" ( echo [ERROR] --dest requires a directory & exit /b 2 )
set "DEST_DIR=%~f2"
shift & shift
goto parse_args

:args_done

set "PAPER_DIR=%REPO_ROOT%\papers\%SLUG%"
set "PDF=%PAPER_DIR%\latex\main.pdf"

if not exist "%PAPER_DIR%\" (
    echo [ERROR] No such paper: papers\%SLUG%
    echo         Look in %REPO_ROOT%\papers\ for the available ones.
    exit /b 1
)

if "%BUILD%"=="1" (
    call "%REPO_ROOT%\scripts\papers\%SLUG%\build.bat"
    if errorlevel 1 exit /b 1
)

if not exist "%PDF%" (
    echo [ERROR] No built PDF at papers\%SLUG%\latex\main.pdf
    echo         Build it first: scripts\papers\%SLUG%\build.bat
    echo         ^(or re-run this script with --build^)
    exit /b 1
)

if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"
copy /y "%PDF%" "%DEST_DIR%\%SLUG%.pdf" >nul || (
    echo [ERROR] Copy failed.
    exit /b 1
)
echo Copied: %DEST_DIR%\%SLUG%.pdf

if "%OPEN%"=="1" start "" "%DEST_DIR%\%SLUG%.pdf"
exit /b 0

:usage
echo to_output.bat -- Copy a built paper PDF into a shared output folder
echo.
echo Usage:
echo     scripts\to_output.bat [slug] [options]
echo.
echo Options:
echo     -b, --build       Run scripts\papers\^<slug^>\build.bat before copying.
echo     -d, --dest DIR    Destination directory ^(default: PAPER_OUTPUT_DIR,
echo                       or %%USERPROFILE%%\paper_output^).
echo     -o, --open        Open the copied PDF in the default viewer.
echo     -h, --help, /?    Show this help text.
exit /b 0
