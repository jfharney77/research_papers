#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile ACM LaTeX document to PDF (WSL / Linux / macOS)
#
# Usage:
#   From the repository root:
#     bash script/latex/acm/build.sh
#
#   Or make it executable and run directly:
#     chmod +x script/latex/acm/build.sh
#     ./script/latex/acm/build.sh
#
#   Pass a custom source path as the first argument:
#     bash script/latex/acm/build.sh /path/to/latex/acm
#
# Requirements:
#   - pdflatex and bibtex in your PATH
#   - Ubuntu/Debian (WSL): sudo apt install texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended
#   - acmart.cls -- committed locally in latex/acm/ (v2.03, Feb 2024)
#     To update: replace acmart.cls and the acm*.bbx/cbx/dbx files in latex/acm/
#     with newer versions from https://ctan.org/pkg/acmart
# =============================================================================

set -euo pipefail

# --- Resolve the latex/acm source directory ---------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ge 1 ]]; then
    SRC_DIR="$(realpath "$1")"
else
    # Default: three levels up from script/latex/acm/ lands at repo root,
    # then down into latex/acm/
    SRC_DIR="$(realpath "${SCRIPT_DIR}/../../../latex/acm")"
fi

# --- Validate source directory ----------------------------------------------
if [[ ! -f "${SRC_DIR}/main.tex" ]]; then
    echo "[ERROR] Cannot find main.tex in: ${SRC_DIR}"
    echo "        Run this script from the repository root, or pass the"
    echo "        path to the latex/acm directory as an argument."
    exit 1
fi

# --- Check that acmart.cls is present ---------------------------------------
if [[ ! -f "${SRC_DIR}/acmart.cls" ]]; then
    echo "[ERROR] acmart.cls not found in: ${SRC_DIR}"
    echo "        Download the latest version from: https://ctan.org/pkg/acmart"
    echo "        and place acmart.cls and the acm*.bbx/cbx/dbx files in: ${SRC_DIR}"
    exit 1
fi

# --- Auto-install texlive packages if pdflatex or bibtex are missing --------
MISSING_PKGS=()
command -v pdflatex &>/dev/null || MISSING_PKGS+=("pdflatex")
command -v bibtex   &>/dev/null || MISSING_PKGS+=("bibtex")

if [[ ${#MISSING_PKGS[@]} -gt 0 && "${LATEX_AUTO_INSTALL:-0}" != "1" ]]; then
    echo "[ERROR] Missing commands: ${MISSING_PKGS[*]}"
    echo "        TeX Live is not installed and host auto-install is disabled."
    echo "        Install TeX Live, set LATEX_AUTO_INSTALL=1 to allow apt-get,"
    echo "        or build with LATEX_SANDBOX=docker."
    exit 1
fi

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
    echo "[INFO] Missing commands: ${MISSING_PKGS[*]}"

    if ! command -v apt-get &>/dev/null; then
        echo "[ERROR] apt-get not found. Please install texlive-latex-base manually"
        echo "        and ensure pdflatex and bibtex are in your PATH."
        exit 1
    fi

    echo "[INFO] Installing texlive packages via apt-get (requires sudo) ..."
    sudo apt-get update -qq
    sudo apt-get install -y texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended

    # Re-check after install
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
echo " Building ACM LaTeX document"
echo " Source : ${SRC_DIR}"
echo "============================================================"
echo ""

pushd "${SRC_DIR}" > /dev/null

echo "[1/4] pdflatex (first pass) ..."
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

echo ""
echo "[2/4] bibtex (bibliography) ..."
bibtex main

echo ""
echo "[3/4] pdflatex (second pass -- resolving citations) ..."
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

echo ""
echo "[4/4] pdflatex (third pass -- resolving cross-references) ..."
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode main.tex

popd > /dev/null

echo ""
echo "============================================================"
echo " Build complete!"
echo " Output : ${SRC_DIR}/main.pdf"
echo "============================================================"
echo ""
