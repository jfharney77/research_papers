#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile AAAI LaTeX document to PDF (WSL / Linux / macOS)
#
# Usage:
#   From the repository root:
#     bash script/latex/aaai/build.sh
#
#   Or make it executable and run directly:
#     chmod +x script/latex/aaai/build.sh
#     ./script/latex/aaai/build.sh
#
#   Pass a custom source path as the first argument:
#     bash script/latex/aaai/build.sh /path/to/latex/aaai
#
# Requirements:
#   - pdflatex and bibtex in your PATH
#   - Ubuntu/Debian (WSL): sudo apt install texlive-latex-base texlive-publishers
#   - unzip (or python3) for style file extraction
#
# Style files:
#   aaai2026.sty and aaai2026.bst are extracted from the author kit zip
#   bundled in this repository at style_kits/AAAI/.
#   To update for a new year, place the new AuthorKitYY.zip in style_kits/AAAI/
#   and update STYLE_YEAR and STY_FILE below.
# =============================================================================

set -euo pipefail

# =============================================================================
# STYLE FILE CONFIGURATION -- update each year
# =============================================================================
STYLE_YEAR="2026"
STY_FILE="aaai2026.sty"
BST_FILE="aaai2026.bst"
# =============================================================================

# --- Resolve paths ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(realpath "${SCRIPT_DIR}/../../../")"

if [[ $# -ge 1 ]]; then
    SRC_DIR="$(realpath "$1")"
else
    SRC_DIR="${REPO_ROOT}/latex/aaai"
fi

# --- Validate source directory ----------------------------------------------
if [[ ! -f "${SRC_DIR}/main.tex" ]]; then
    echo "[ERROR] Cannot find main.tex in: ${SRC_DIR}"
    echo "        Run this script from the repository root, or pass the"
    echo "        path to the latex/aaai directory as an argument."
    exit 1
fi

# --- Check that AAAI style files are present --------------------------------
if [[ ! -f "${SRC_DIR}/${STY_FILE}" ]]; then
    echo "[ERROR] ${STY_FILE} not found in: ${SRC_DIR}"
    echo "        Download the AAAI author kit from:"
    echo "        https://aaai.org/conference/aaai/aaai-${STYLE_YEAR}/aaai-${STYLE_YEAR}-author-kit/"
    echo "        and extract ${STY_FILE} and ${BST_FILE} into: ${SRC_DIR}"
    exit 1
fi

# --- Auto-install texlive packages if pdflatex or bibtex are missing --------
MISSING_PKGS=()
command -v pdflatex &>/dev/null || MISSING_PKGS+=("pdflatex")
command -v bibtex   &>/dev/null || MISSING_PKGS+=("bibtex")

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
    echo "[INFO] Missing commands: ${MISSING_PKGS[*]}"

    if ! command -v apt-get &>/dev/null; then
        echo "[ERROR] apt-get not found. Please install texlive-latex-base manually"
        echo "        and ensure pdflatex and bibtex are in your PATH."
        exit 1
    fi

    echo "[INFO] Installing texlive packages via apt-get (requires sudo) ..."
    sudo apt-get update -qq
    sudo apt-get install -y texlive-latex-base texlive-publishers texlive-latex-extra

    if ! command -v pdflatex &>/dev/null || ! command -v bibtex &>/dev/null; then
        echo "[ERROR] Installation completed but pdflatex/bibtex still not found."
        echo "        Try: sudo apt install texlive-full"
        exit 1
    fi

    echo "[INFO] Installation successful."
fi

# --- Clean stale auxiliary files to prevent duplicate \bibstyle errors -----
echo "[0/4] Cleaning auxiliary files ..."
for ext in aux bbl blg lof lot toc out; do
    rm -f "${SRC_DIR}/main.${ext}"
done

# --- Build ------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Building AAAI LaTeX document"
echo " Source : ${SRC_DIR}"
echo "============================================================"
echo ""

pushd "${SRC_DIR}" > /dev/null

echo "[1/4] pdflatex (first pass) ..."
pdflatex -interaction=nonstopmode main.tex

echo ""
echo "[2/4] bibtex (bibliography) ..."
bibtex main

echo ""
echo "[3/4] pdflatex (second pass -- resolving citations) ..."
pdflatex -interaction=nonstopmode main.tex

echo ""
echo "[4/4] pdflatex (third pass -- resolving cross-references) ..."
pdflatex -interaction=nonstopmode main.tex

popd > /dev/null

echo ""
echo "============================================================"
echo " Build complete!"
echo " Output : ${SRC_DIR}/main.pdf"
echo "============================================================"
echo ""
