@echo off
rem ==========================================================================
rem  latex_to_word.bat -- Convert a paper's LaTeX back into a Word document
rem  (Windows)
rem
rem  Batch equivalent of scripts/latex_to_word.sh, the reverse of
rem  word_to_latex. Uses pandoc to turn papers\<slug>\latex\main.tex into a
rem  .docx, resolving \input{} section files and \cite{} keys against
rem  references.bib along the way.
rem
rem  Usage:
rem      scripts\latex_to_word.bat                    (APIP)
rem      scripts\latex_to_word.bat <slug>             (another paper)
rem      scripts\latex_to_word.bat --out draft.docx   (explicit output path)
rem
rem  Options:
rem      -o, --out FILE    Output .docx path. Default:
rem                        papers\<slug>\manuscript\<slug>_from_latex.docx
rem      -s, --src DIR     LaTeX directory to convert (default: papers\<slug>\latex).
rem      -r, --reference F Word file whose styles the output should inherit.
rem                        Default: templates\word\reference.docx if it exists.
rem      -w, --windows     Also copy the result to the paper output folder
rem                        (PAPER_OUTPUT_DIR, or %USERPROFILE%\paper_output).
rem      -h, --help, /?    Show this help text.
rem
rem  Requires pandoc on PATH: https://pandoc.org/installing.html
rem
rem  A round trip is lossy in both directions. Treat the output as a
rem  review/comment copy for collaborators, not as the source of truth --
rem  that stays in papers\<slug>\latex\.
rem ==========================================================================
setlocal EnableDelayedExpansion

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"

set "SLUG=apip"
set "OUT="
set "SRC="
set "REFERENCE="
set "TO_WINDOWS=0"

rem --- Parse arguments ------------------------------------------------------
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="-o"           goto set_out
if /i "%~1"=="--out"        goto set_out
if /i "%~1"=="-s"           goto set_src
if /i "%~1"=="--src"        goto set_src
if /i "%~1"=="-r"           goto set_ref
if /i "%~1"=="--reference"  goto set_ref
if /i "%~1"=="-w"           ( set "TO_WINDOWS=1" & shift & goto parse_args )
if /i "%~1"=="--windows"    ( set "TO_WINDOWS=1" & shift & goto parse_args )
if /i "%~1"=="-h"           goto usage
if /i "%~1"=="--help"       goto usage
if /i "%~1"=="/?"           goto usage
set "ARG=%~1"
if "%ARG:~0,1%"=="-" (
    echo [ERROR] Unknown option: %~1
    echo         Run "%~nx0 --help" for usage.
    exit /b 2
)
set "SLUG=%~1"
shift
goto parse_args

:set_out
if "%~2"=="" ( echo [ERROR] --out requires a file & exit /b 2 )
set "OUT=%~f2"
shift & shift
goto parse_args

:set_src
if "%~2"=="" ( echo [ERROR] --src requires a directory & exit /b 2 )
set "SRC=%~f2"
shift & shift
goto parse_args

:set_ref
if "%~2"=="" ( echo [ERROR] --reference requires a file & exit /b 2 )
set "REFERENCE=%~f2"
shift & shift
goto parse_args

:args_done

set "PAPER_DIR=%REPO_ROOT%\papers\%SLUG%"
if not exist "%PAPER_DIR%\" (
    echo [ERROR] No such paper: papers\%SLUG%
    echo         Look in %REPO_ROOT%\papers\ for the available ones.
    exit /b 1
)

if not defined SRC set "SRC=%PAPER_DIR%\latex"
if not exist "%SRC%\main.tex" (
    echo [ERROR] Cannot find main.tex in: %SRC%
    exit /b 1
)

if not defined OUT set "OUT=%PAPER_DIR%\manuscript\%SLUG%_from_latex.docx"

rem --- Require pandoc -------------------------------------------------------
where pandoc >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pandoc not found -- it is what does the LaTeX to Word conversion.
    echo         Install it: https://pandoc.org/installing.html
    echo         ^(winget install --id JohnMacFarlane.Pandoc^)
    exit /b 1
)

rem --- Reference styles -----------------------------------------------------
if not defined REFERENCE if exist "%REPO_ROOT%\templates\word\reference.docx" (
    set "REFERENCE=%REPO_ROOT%\templates\word\reference.docx"
)

rem Render \cite{} keys into real text rather than dropping them, when there
rem is a bibliography with actual entries to render from.
set "BIB_ARGS="
if exist "%SRC%\references.bib" (
    findstr /c:"@" "%SRC%\references.bib" >nul 2>&1 && set "BIB_ARGS=--citeproc --bibliography=references.bib"
)
if not defined BIB_ARGS (
    echo [WARN] No bibliography entries in %SRC%\references.bib --
    echo        \cite{} keys will render as-is.
)

set "REF_ARGS="
if defined REFERENCE set "REF_ARGS=--reference-doc=%REFERENCE%"

rem --- Convert --------------------------------------------------------------
for %%F in ("%OUT%") do if not exist "%%~dpF" mkdir "%%~dpF"

echo.
echo ============================================================
echo  Converting %SLUG% LaTeX to Word
echo  Source : %SRC%\main.tex
echo ============================================================
echo.

pushd "%SRC%"
rem Pandoc's --resource-path separator is ";" on Windows. It resolves
rem \input{sections\...} and \includegraphics against the source dir.
pandoc main.tex --from=latex --to=docx --output="%OUT%" --resource-path=".;sections;figures;..\figures;..\..\templates\assets\figures" --standalone !BIB_ARGS! !REF_ARGS!
if errorlevel 1 ( popd & exit /b 1 )
popd

echo Wrote: %OUT%
echo.
echo Round trips are lossy: this is a review copy for collaborators.
echo The source of truth stays in papers\%SLUG%\latex\.

if "%TO_WINDOWS%"=="1" (
    if not defined PAPER_OUTPUT_DIR set "PAPER_OUTPUT_DIR=%USERPROFILE%\paper_output"
    if not exist "!PAPER_OUTPUT_DIR!" mkdir "!PAPER_OUTPUT_DIR!"
    copy /y "%OUT%" "!PAPER_OUTPUT_DIR!\" >nul
    for %%F in ("%OUT%") do echo Copied: !PAPER_OUTPUT_DIR!\%%~nxF
)
exit /b 0

:usage
echo latex_to_word.bat -- Convert a paper's LaTeX back into a Word document
echo.
echo Usage:
echo     scripts\latex_to_word.bat [slug] [options]
echo.
echo Options:
echo     -o, --out FILE    Output .docx path ^(default:
echo                       papers\^<slug^>\manuscript\^<slug^>_from_latex.docx^).
echo     -s, --src DIR     LaTeX directory to convert ^(default: papers\^<slug^>\latex^).
echo     -r, --reference F Word file whose styles the output should inherit.
echo     -w, --windows     Also copy the result to the paper output folder.
echo     -h, --help, /?    Show this help text.
exit /b 0
