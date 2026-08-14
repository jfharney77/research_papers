#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile the NeurIPS template (templates/latex/neurips) to PDF
#
# Usage:
#   bash scripts/templates/neurips/build.sh [-c|--clean] [-q|--quiet] [-s|--src DIR]
#
# Style files:
#   neurips_<year>.sty is downloaded from the NeurIPS site on first build and
#   then version-controlled. Update STYLE_YEAR and STYLE_URL below each year;
#   find the current link at
#   https://neurips.cc/Conferences/<YEAR>/PaperInformation/StyleFiles
#
# Requirements: pdflatex, bibtex, plus curl and unzip (or python3) for the
# first-run style download.
# =============================================================================
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/latex_build.sh"

# --- Style file configuration -- update each year ---------------------------
STYLE_YEAR="2025"
STYLE_URL="https://media.neurips.cc/Conferences/NeurIPS2025/Styles.zip"

LATEX_NAME="NeurIPS template"
LATEX_SRC="${REPO_ROOT}/templates/latex/neurips"
TEXLIVE_PKGS="texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended texlive-science"

latex_parse_args "$@"

# --- Download the NeurIPS style file if it is not already present -----------
if ! ls "${LATEX_SRC}"/neurips_*.sty &>/dev/null; then
    echo "[INFO] NeurIPS style file not found. Attempting download ..."

    if ! command -v curl &>/dev/null; then
        echo "[ERROR] curl not found. Cannot auto-download the style file."
        echo "        Install curl (sudo apt install curl) or download"
        echo "        neurips_${STYLE_YEAR}.sty manually from:"
        echo "        https://neurips.cc/Conferences/${STYLE_YEAR}/PaperInformation/StyleFiles"
        echo "        and place it in: ${LATEX_SRC}"
        exit 1
    fi

    ZIP_FILE="${LATEX_SRC}/neurips_${STYLE_YEAR}.zip"

    echo "[INFO] Downloading: ${STYLE_URL}"
    curl -L --fail --show-error -o "${ZIP_FILE}" "${STYLE_URL}"

    echo "[INFO] Extracting style file ..."
    if command -v unzip &>/dev/null; then
        unzip -o -j "${ZIP_FILE}" "*.sty" -d "${LATEX_SRC}"
    else
        # Fallback to Python (available in most WSL environments)
        python3 -c "
import zipfile, os
with zipfile.ZipFile('${ZIP_FILE}') as z:
    for name in z.namelist():
        if name.endswith('.sty'):
            z.extract(name, '${LATEX_SRC}')
            # Flatten any subdirectory from the zip
            extracted = os.path.join('${LATEX_SRC}', name)
            target = os.path.join('${LATEX_SRC}', os.path.basename(name))
            if extracted != target:
                os.rename(extracted, target)
"
    fi
    rm -f "${ZIP_FILE}"

    if ! ls "${LATEX_SRC}"/neurips_*.sty &>/dev/null; then
        echo "[ERROR] Extraction completed but neurips_*.sty not found in: ${LATEX_SRC}"
        echo "        Download manually from:"
        echo "        https://neurips.cc/Conferences/${STYLE_YEAR}/PaperInformation/StyleFiles"
        exit 1
    fi

    echo "[INFO] Style file downloaded successfully."
    echo ""
fi

require_texlive
latex_build
