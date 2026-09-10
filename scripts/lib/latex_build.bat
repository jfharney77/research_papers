@echo off
rem ==========================================================================
rem  latex_build.bat -- shared LaTeX build engine (Windows cmd.exe)
rem
rem  Batch counterpart of scripts/lib/latex_build.sh. Never run directly --
rem  called by the thin wrappers in scripts\papers\<name>\build.bat and
rem  scripts\templates\<conference>\build.bat:
rem
rem      @echo off
rem      setlocal
rem      for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
rem      set "LATEX_NAME=APIP paper"
rem      set "LATEX_SRC=%REPO_ROOT%\papers\apip\latex"
rem      call "%~dp0..\..\lib\latex_build.bat" %*
rem      exit /b %errorlevel%
rem
rem  Flags every wrapper inherits:
rem      -c, --clean       Delete .aux/.bbl/.blg/.log/.out before building. Use
rem                        after editing references.bib or renaming a \label,
rem                        when stale aux files cause spurious "undefined
rem                        reference" warnings.
rem      -q, --quiet       Suppress pdflatex/bibtex output; summary only.
rem      -s, --src DIR     Build a different directory than the wrapper's default.
rem      -h, --help, /?    Show usage.
rem
rem  Knobs a wrapper may set before the call:
rem      LATEX_NAME          Human-readable label for the banner. Required.
rem      LATEX_SRC           Directory holding main.tex. Required.
rem      LATEX_ALWAYS_CLEAN  1 to clean aux files on every build (AAAI needs
rem                          this -- stale .aux triggers duplicate \bibstyle
rem                          errors).
rem
rem  Requirements: pdflatex and bibtex on PATH. Install MiKTeX
rem  (https://miktex.org) or TeX Live for Windows (https://tug.org/texlive).
rem  There is no auto-install path on Windows -- the LATEX_AUTO_INSTALL escape
rem  hatch in the shell engine is Debian/apt-specific.
rem ==========================================================================

setlocal EnableDelayedExpansion

if not defined LATEX_NAME set "LATEX_NAME=LaTeX document"
if not defined LATEX_ALWAYS_CLEAN set "LATEX_ALWAYS_CLEAN=0"
set "CLEAN=%LATEX_ALWAYS_CLEAN%"
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
echo         Run with --help for usage.
exit /b 2

:set_src
if "%~2"=="" (
    echo [ERROR] --src requires a directory
    exit /b 2
)
set "LATEX_SRC=%~f2"
shift
shift
goto parse_args

:args_done

rem --- Validate source directory --------------------------------------------
if not defined LATEX_SRC (
    echo [ERROR] LATEX_SRC is unset -- the wrapper script is incomplete.
    exit /b 1
)
if not exist "%LATEX_SRC%\main.tex" (
    echo [ERROR] Cannot find main.tex in: %LATEX_SRC%
    echo         Run this script from anywhere, or pass another directory
    echo         with --src.
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
echo  Building %LATEX_NAME%
echo  Source : %LATEX_SRC%
echo ============================================================
echo.

pushd "%LATEX_SRC%" || (
    echo [ERROR] Could not enter: %LATEX_SRC%
    exit /b 1
)

if "%CLEAN%"=="1" (
    echo [0/4] cleaning auxiliary files ...
    del /q main.aux main.bbl main.blg main.log main.out main.toc main.lof main.lot main.synctex.gz 2>nul
)

echo [1/4] pdflatex ^(first pass^) ...
call :run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex
if errorlevel 1 goto build_failed

echo.
echo [2/4] bibtex ^(bibliography^) ...
rem bibtex exits nonzero when a document has no \cite commands or no \bibdata
rem -- normal for a draft with the bibliography not yet wired up. Report and
rem continue; genuine .bib errors still surface in main.blg and as undefined
rem citations in the summary below.
call :run bibtex main
if errorlevel 1 (
    echo [WARN] bibtex reported errors ^(see %LATEX_SRC%\main.blg^).
    echo        Expected when the document has no citations yet.
)

echo.
echo [3/4] pdflatex ^(second pass -- resolving citations^) ...
call :run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex
if errorlevel 1 goto build_failed

echo.
echo [4/4] pdflatex ^(third pass -- resolving cross-references^) ...
call :run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex
if errorlevel 1 goto build_failed

rem --- Report page count and warnings worth acting on -----------------------
set "PAGES="
for /f "tokens=5 delims=( " %%a in ('findstr /c:"Output written on main.pdf" main.log 2^>nul') do set "PAGES=%%a"

set "HAS_WARNINGS=0"
findstr /c:"Undefined control sequence" /c:"LaTeX Warning: Reference" /c:"LaTeX Warning: Citation" /c:"Overfull" main.log >nul 2>&1 && set "HAS_WARNINGS=1"

popd

echo.
echo ============================================================
echo  Build complete!
if defined PAGES (
    echo  Output : %LATEX_SRC%\main.pdf  ^(%PAGES% pages^)
) else (
    echo  Output : %LATEX_SRC%\main.pdf
)
if "%HAS_WARNINGS%"=="1" (
    echo ------------------------------------------------------------
    echo  Warnings ^(see %LATEX_SRC%\main.log for detail^):
    findstr /c:"Undefined control sequence" /c:"LaTeX Warning: Reference" /c:"LaTeX Warning: Citation" /c:"Overfull" "%LATEX_SRC%\main.log"
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
echo [ERROR] Build failed. See %LATEX_SRC%\main.log for the LaTeX error.
exit /b 1

:usage
echo Compile %LATEX_NAME% to PDF ^(pdflatex - bibtex - pdflatex - pdflatex^).
echo.
echo Options:
echo     -c, --clean       Delete .aux/.bbl/.blg/.log/.out before building.
echo                       Use after editing references.bib or renaming a
echo                       \label, when stale aux files cause spurious
echo                       "undefined reference" warnings.
echo     -q, --quiet       Suppress pdflatex/bibtex output; summary only.
echo     -s, --src DIR     Build a different directory
echo                       ^(default: %LATEX_SRC%^).
echo     -h, --help, /?    Show this help text.
echo.
echo Requirements:
echo     pdflatex and bibtex on PATH ^(MiKTeX or TeX Live for Windows^).
exit /b 0
