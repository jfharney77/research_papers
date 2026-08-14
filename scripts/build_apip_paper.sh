#!/usr/bin/env bash
# =============================================================================
# build_apip_paper.sh -- Compile the APIP paper (papers/apip) to PDF
#
# The paper is "Your Agent is Underperforming: The Case for Agent Performance
# Improvement Plans", converted from research/apip/APIP_Paper_v8_tracked.docx
# into the IEEE conference style from ieee_agc/.
#
# Usage:
#   From the repository root:
#     bash scripts/build_apip_paper.sh
#
#   Or make it executable and run directly:
#     chmod +x scripts/build_apip_paper.sh
#     ./scripts/build_apip_paper.sh
#
# Options:
#   -c, --clean       Remove auxiliary files (.aux/.bbl/.blg/.log/.out) before
#                     building. Use this after editing references.bib or after
#                     renaming a \label, when stale aux files can cause
#                     spurious "undefined reference" warnings.
#   -q, --quiet       Suppress pdflatex/bibtex output; report only the summary.
#   -s, --src DIR     Build a different paper directory (default: papers/apip).
#   -h, --help        Show this help text.
#
# Requirements:
#   - pdflatex and bibtex in your PATH
#   - Ubuntu/Debian (WSL): sudo apt install texlive-latex-base \
#       texlive-latex-recommended texlive-publishers texlive-latex-extra \
#       texlive-fonts-recommended
#   IEEEtran.cls and IEEEtran.bst are vendored in papers/apip/, so no IEEE
#   TeX Live package is required.
#
#   Host auto-install is disabled by default; set LATEX_AUTO_INSTALL=1 to let
#   this script apt-get TeX Live for you.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SRC_DIR="${REPO_ROOT}/papers/apip"
CLEAN=0
QUIET=0

# --- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--clean) CLEAN=1; shift ;;
        -q|--quiet) QUIET=1; shift ;;
        -s|--src)
            [[ $# -ge 2 ]] || { echo "[ERROR] --src requires a directory"; exit 2; }
            SRC_DIR="$(realpath "$2")"; shift 2 ;;
        -h|--help)
            # Print the comment header (everything after the shebang, up to
            # the first non-comment line) with the leading "# " stripped.
            sed -n '2,$p' "${BASH_SOURCE[0]}" | sed -n '/^#/!q;s/^# \{0,1\}//;p'
            exit 0 ;;
        *)
            echo "[ERROR] Unknown argument: $1"
            echo "        Run '$0 --help' for usage."
            exit 2 ;;
    esac
done

# --- Validate source directory ----------------------------------------------
if [[ ! -f "${SRC_DIR}/main.tex" ]]; then
    echo "[ERROR] Cannot find main.tex in: ${SRC_DIR}"
    echo "        Expected the APIP paper at papers/apip/, or pass another"
    echo "        directory with --src."
    exit 1
fi

# --- Check for pdflatex / bibtex --------------------------------------------
MISSING_PKGS=()
command -v pdflatex &>/dev/null || MISSING_PKGS+=("pdflatex")
command -v bibtex   &>/dev/null || MISSING_PKGS+=("bibtex")

if [[ ${#MISSING_PKGS[@]} -gt 0 && "${LATEX_AUTO_INSTALL:-0}" != "1" ]]; then
    echo "[ERROR] Missing commands: ${MISSING_PKGS[*]}"
    echo "        TeX Live is not installed and host auto-install is disabled."
    echo "        Install TeX Live or set LATEX_AUTO_INSTALL=1 to allow apt-get."
    exit 1
fi

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
    echo "[INFO] Missing commands: ${MISSING_PKGS[*]}"

    if ! command -v apt-get &>/dev/null; then
        echo "[ERROR] apt-get not found. Please install texlive-latex-base manually"
        echo "        and ensure pdflatex and bibtex are in your PATH."
        exit 1
    fi

    echo "[INFO] Installing TeX Live via apt-get (requires sudo) ..."
    sudo apt-get update -qq
    sudo apt-get install -y texlive-latex-base texlive-latex-recommended \
        texlive-publishers texlive-latex-extra texlive-fonts-recommended

    if ! command -v pdflatex &>/dev/null || ! command -v bibtex &>/dev/null; then
        echo "[ERROR] Installation completed but pdflatex/bibtex still not found."
        echo "        Try: sudo apt install texlive-full"
        exit 1
    fi

    echo "[INFO] Installation successful."
fi

# --- Build ------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Building the APIP paper"
echo " Source : ${SRC_DIR}"
echo "============================================================"
echo ""

pushd "${SRC_DIR}" > /dev/null

if [[ ${CLEAN} -eq 1 ]]; then
    echo "[0/4] cleaning auxiliary files ..."
    rm -f main.aux main.bbl main.blg main.log main.out main.toc main.synctex.gz
fi

run() {
    if [[ ${QUIET} -eq 1 ]]; then
        "$@" > /dev/null
    else
        "$@"
    fi
}

echo "[1/4] pdflatex (first pass) ..."
run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

echo ""
echo "[2/4] bibtex (bibliography) ..."
run bibtex main

echo ""
echo "[3/4] pdflatex (second pass -- resolving citations) ..."
run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

echo ""
echo "[4/4] pdflatex (third pass -- resolving cross-references) ..."
run pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

# --- Report warnings worth acting on ----------------------------------------
WARNINGS="$(grep -E "Undefined (control sequence|reference|citation)|LaTeX Warning: (Reference|Citation)|Overfull" main.log || true)"

PAGES="$(grep -oE "Output written on main\.pdf \([0-9]+ page" main.log | grep -oE "[0-9]+" | tail -1 || true)"

popd > /dev/null

echo ""
echo "============================================================"
echo " Build complete!"
echo " Output : ${SRC_DIR}/main.pdf${PAGES:+  (${PAGES} pages)}"
if [[ -n "${WARNINGS}" ]]; then
    echo "------------------------------------------------------------"
    echo " Warnings (see ${SRC_DIR}/main.log for detail):"
    echo "${WARNINGS}" | sed 's/^/   /'
fi
echo "============================================================"
echo ""
