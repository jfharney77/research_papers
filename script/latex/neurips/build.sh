#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile NeurIPS LaTeX document to PDF (WSL / Linux / macOS)
#
# Usage:
#   From the repository root:
#     bash script/latex/neurips/build.sh
#
#   Or make it executable and run directly:
#     chmod +x script/latex/neurips/build.sh
#     ./script/latex/neurips/build.sh
#
#   Pass a custom source path as the first argument:
#     bash script/latex/neurips/build.sh /path/to/latex/neurips
#
# Requirements:
#   - pdflatex and bibtex in your PATH
#   - Ubuntu/Debian (WSL): sudo apt install texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended texlive-science
#   - curl and unzip for automatic style file download
# =============================================================================

set -euo pipefail

# =============================================================================
# STYLE FILE CONFIGURATION
# Update STYLE_YEAR and STYLE_URL each year when NeurIPS releases new files.
# Find the latest download link at:
#   https://neurips.cc/Conferences/<YEAR>/PaperInformation/StyleFiles
# =============================================================================
STYLE_YEAR="2025"
#STYLE_URL="https://media.nips.cc/Conferences/2025/Styles/neurips_2025.zip"
STYLE_URL="https://media.neurips.cc/Conferences/NeurIPS2025/Styles.zip"
# =============================================================================

# --- Resolve the latex/neurips source directory -----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ge 1 ]]; then
    SRC_DIR="$(realpath "$1")"
else
    # Default: three levels up from script/latex/neurips/ lands at repo root,
    # then down into latex/neurips/
    SRC_DIR="$(realpath "${SCRIPT_DIR}/../../../latex/neurips")"
fi

# --- Validate source directory ----------------------------------------------
if [[ ! -f "${SRC_DIR}/main.tex" ]]; then
    echo "[ERROR] Cannot find main.tex in: ${SRC_DIR}"
    echo "        Run this script from the repository root, or pass the"
    echo "        path to the latex/neurips directory as an argument."
    exit 1
fi

# --- Download NeurIPS style file if not already present ---------------------
if ! ls "${SRC_DIR}"/neurips_*.sty &>/dev/null; then
    echo "[INFO] NeurIPS style file not found. Attempting download ..."

    if ! command -v curl &>/dev/null; then
        echo "[ERROR] curl not found. Cannot auto-download the style file."
        echo "        Install curl (sudo apt install curl) or manually download"
        echo "        neurips_${STYLE_YEAR}.sty from:"
        echo "        https://neurips.cc/Conferences/${STYLE_YEAR}/PaperInformation/StyleFiles"
        echo "        and place it in: ${SRC_DIR}"
        exit 1
    fi

    ZIP_FILE="${SRC_DIR}/neurips_${STYLE_YEAR}.zip"

    echo "[INFO] Downloading: ${STYLE_URL}"
    curl -L --fail --show-error -o "${ZIP_FILE}" "${STYLE_URL}"

    echo "[INFO] Extracting style file ..."
    if command -v unzip &>/dev/null; then
        unzip -o -j "${ZIP_FILE}" "*.sty" -d "${SRC_DIR}"
    else
        # Fallback to Python (available in most WSL environments)
        python3 -c "
import zipfile, sys, os
with zipfile.ZipFile('${ZIP_FILE}') as z:
    for name in z.namelist():
        if name.endswith('.sty'):
            z.extract(name, '${SRC_DIR}')
            # Flatten any subdirectory from the zip
            extracted = os.path.join('${SRC_DIR}', name)
            target = os.path.join('${SRC_DIR}', os.path.basename(name))
            if extracted != target:
                os.rename(extracted, target)
"
    fi
    rm -f "${ZIP_FILE}"

    # Verify extraction succeeded
    if ! ls "${SRC_DIR}"/neurips_*.sty &>/dev/null; then
        echo "[ERROR] Extraction completed but neurips_*.sty not found in: ${SRC_DIR}"
        echo "        Try downloading manually from:"
        echo "        https://neurips.cc/Conferences/${STYLE_YEAR}/PaperInformation/StyleFiles"
        exit 1
    fi

    echo "[INFO] Style file downloaded successfully."
    echo ""
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
echo " Building NeurIPS LaTeX document"
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
