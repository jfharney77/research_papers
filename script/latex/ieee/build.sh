#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile IEEE LaTeX document to PDF (WSL / Linux / macOS)
#
# Usage:
#   From the repository root:
#     bash script/latex/ieee/build.sh
#
#   Or make it executable and run directly:
#     chmod +x script/latex/ieee/build.sh
#     ./script/latex/ieee/build.sh
#
#   Pass a custom source path as the first argument:
#     bash script/latex/ieee/build.sh /path/to/latex/ieee
#
# Requirements:
#   - pdflatex and bibtex in your PATH
#   - Ubuntu/Debian (WSL): sudo apt install texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended texlive-science
# =============================================================================

set -euo pipefail

# --- Resolve the latex/ieee source directory --------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ge 1 ]]; then
    SRC_DIR="$(realpath "$1")"
else
    # Default: three levels up from script/latex/ieee/ lands at repo root,
    # then down into latex/ieee/
    SRC_DIR="$(realpath "${SCRIPT_DIR}/../../../latex/ieee")"
fi

# --- Validate source directory ----------------------------------------------
if [[ ! -f "${SRC_DIR}/main.tex" ]]; then
    echo "[ERROR] Cannot find main.tex in: ${SRC_DIR}"
    echo "        Run this script from the repository root, or pass the"
    echo "        path to the latex/ieee directory as an argument."
    exit 1
fi

# --- Auto-install texlive-latex-base if pdflatex or bibtex are missing ------
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

    echo "[INFO] Installing texlive-latex-base via apt-get (requires sudo) ..."
    sudo apt-get update -qq
    sudo apt-get install -y texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended texlive-science

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
echo " Building IEEE LaTeX document"
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
