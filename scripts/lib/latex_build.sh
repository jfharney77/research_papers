#!/usr/bin/env bash
# =============================================================================
# latex_build.sh -- shared LaTeX build engine (WSL / Linux / macOS)
#
# Sourced by the thin wrappers in scripts/papers/<name>/build.sh and
# scripts/templates/<conference>/build.sh. Nothing here runs on its own.
#
# A wrapper sets LATEX_NAME + LATEX_SRC, optionally checks for style files,
# then calls latex_build. Everything else -- flag parsing, the TeX Live check,
# the four-pass build, and the main.log warning report -- lives here so a fix
# lands once for every paper and every conference template.
#
#   #!/usr/bin/env bash
#   set -euo pipefail
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/latex_build.sh"
#
#   LATEX_NAME="APIP paper"
#   LATEX_SRC="${REPO_ROOT}/papers/apip/latex"
#   latex_parse_args "$@"
#   require_texlive
#   latex_build
#
# Flags every wrapper inherits:
#   -c, --clean       Remove .aux/.bbl/.blg/.log/.out before building. Use after
#                     editing references.bib or renaming a \label, when stale aux
#                     files cause spurious "undefined reference" warnings.
#   -q, --quiet       Suppress pdflatex/bibtex output; report only the summary.
#   -s, --src DIR     Build a different directory than the wrapper's default.
#   -h, --help        Show the wrapper's header comment as usage text.
#
# Knobs a wrapper may set before calling latex_build:
#   LATEX_NAME          Human-readable label for the banner. Required.
#   LATEX_SRC           Directory holding main.tex. Required.
#   LATEX_ALWAYS_CLEAN  1 to clean aux files on every build (AAAI needs this --
#                       stale .aux triggers duplicate \bibstyle errors).
#   TEXLIVE_PKGS        Override the apt package list for auto-install.
#
# Environment:
#   LATEX_AUTO_INSTALL=1  Allow apt-get to install TeX Live. Off by default.
# =============================================================================

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

LATEX_NAME="${LATEX_NAME:-LaTeX document}"
LATEX_SRC="${LATEX_SRC:-}"
LATEX_ALWAYS_CLEAN="${LATEX_ALWAYS_CLEAN:-0}"
TEXLIVE_PKGS="${TEXLIVE_PKGS:-texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended}"

LATEX_CLEAN=0
LATEX_QUIET=0

# --- Argument parsing -------------------------------------------------------
# Call as: latex_parse_args "$@"   (before any require_* check, so --src applies)
latex_parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--clean) LATEX_CLEAN=1; shift ;;
            -q|--quiet) LATEX_QUIET=1; shift ;;
            -s|--src)
                [[ $# -ge 2 ]] || { echo "[ERROR] --src requires a directory"; exit 2; }
                LATEX_SRC="$(realpath "$2")"; shift 2 ;;
            -h|--help)
                # Print the calling script's header comment, "# " stripped.
                sed -n '2,$p' "$0" | sed -n '/^#/!q;s/^# \{0,1\}//;p'
                exit 0 ;;
            *)
                echo "[ERROR] Unknown argument: $1"
                echo "        Run '$0 --help' for usage."
                exit 2 ;;
        esac
    done
}

# --- Guards -----------------------------------------------------------------
# require_file <path> <hint shown when missing>
require_file() {
    local path="$1" hint="$2"
    if [[ ! -f "${path}" ]]; then
        echo "[ERROR] Missing required file: ${path}"
        echo "        ${hint}"
        exit 1
    fi
}

require_source() {
    if [[ -z "${LATEX_SRC}" ]]; then
        echo "[ERROR] LATEX_SRC is unset -- the wrapper script is incomplete."
        exit 1
    fi
    if [[ ! -f "${LATEX_SRC}/main.tex" ]]; then
        echo "[ERROR] Cannot find main.tex in: ${LATEX_SRC}"
        echo "        Run this script from anywhere, or pass another directory"
        echo "        with --src."
        exit 1
    fi
}

require_texlive() {
    local missing=()
    command -v pdflatex &>/dev/null || missing+=("pdflatex")
    command -v bibtex   &>/dev/null || missing+=("bibtex")
    [[ ${#missing[@]} -eq 0 ]] && return 0

    if [[ "${LATEX_AUTO_INSTALL:-0}" != "1" ]]; then
        echo "[ERROR] Missing commands: ${missing[*]}"
        echo "        TeX Live is not installed and host auto-install is disabled."
        echo "        Install TeX Live, set LATEX_AUTO_INSTALL=1 to allow apt-get,"
        echo "        or build with LATEX_SANDBOX=docker."
        exit 1
    fi

    echo "[INFO] Missing commands: ${missing[*]}"
    if ! command -v apt-get &>/dev/null; then
        echo "[ERROR] apt-get not found. Install TeX Live manually and ensure"
        echo "        pdflatex and bibtex are in your PATH."
        exit 1
    fi

    echo "[INFO] Installing TeX Live via apt-get (requires sudo) ..."
    sudo apt-get update -qq
    # shellcheck disable=SC2086
    sudo apt-get install -y ${TEXLIVE_PKGS}

    if ! command -v pdflatex &>/dev/null || ! command -v bibtex &>/dev/null; then
        echo "[ERROR] Installation completed but pdflatex/bibtex still not found."
        echo "        Try: sudo apt install texlive-full"
        exit 1
    fi
    echo "[INFO] Installation successful."
}

# --- Build ------------------------------------------------------------------
latex_build() {
    require_source

    echo ""
    echo "============================================================"
    echo " Building ${LATEX_NAME}"
    echo " Source : ${LATEX_SRC}"
    echo "============================================================"
    echo ""

    pushd "${LATEX_SRC}" > /dev/null

    if [[ ${LATEX_CLEAN} -eq 1 || ${LATEX_ALWAYS_CLEAN} -eq 1 ]]; then
        echo "[0/4] cleaning auxiliary files ..."
        rm -f main.aux main.bbl main.blg main.log main.out main.toc main.lof \
              main.lot main.synctex.gz
    fi

    _run() {
        if [[ ${LATEX_QUIET} -eq 1 ]]; then "$@" > /dev/null; else "$@"; fi
    }

    echo "[1/4] pdflatex (first pass) ..."
    _run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

    echo ""
    echo "[2/4] bibtex (bibliography) ..."
    # bibtex exits nonzero when a document has no \cite commands or no
    # \bibdata — normal for a draft with the bibliography not yet wired up, and
    # not a reason to abort a document that otherwise compiles. Report and
    # continue; genuine .bib syntax errors still surface in main.blg and as
    # undefined citations in the summary below.
    if ! _run bibtex main; then
        echo "[WARN] bibtex reported errors (see ${LATEX_SRC}/main.blg)."
        echo "       Expected when the document has no citations yet."
    fi

    echo ""
    echo "[3/4] pdflatex (second pass -- resolving citations) ..."
    _run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

    echo ""
    echo "[4/4] pdflatex (third pass -- resolving cross-references) ..."
    _run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

    # --- Report warnings worth acting on ------------------------------------
    local warnings pages
    warnings="$(grep -E "Undefined (control sequence|reference|citation)|LaTeX Warning: (Reference|Citation)|Overfull" main.log || true)"
    pages="$(grep -oE "Output written on main\.pdf \([0-9]+ page" main.log | grep -oE "[0-9]+" | tail -1 || true)"

    popd > /dev/null

    echo ""
    echo "============================================================"
    echo " Build complete!"
    echo " Output : ${LATEX_SRC}/main.pdf${pages:+  (${pages} pages)}"
    if [[ -n "${warnings}" ]]; then
        echo "------------------------------------------------------------"
        echo " Warnings (see ${LATEX_SRC}/main.log for detail):"
        echo "${warnings}" | sed 's/^/   /'
    fi
    echo "============================================================"
    echo ""
}
