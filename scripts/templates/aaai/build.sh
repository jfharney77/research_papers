#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile the AAAI conference template (templates/latex/aaai) to PDF
#
# Usage:
#   bash scripts/templates/aaai/build.sh [-c|--clean] [-q|--quiet] [-s|--src DIR]
#
# Style files:
#   aaai2026.sty and aaai2026.bst are version-controlled in templates/latex/aaai/.
#   To update for a new year, download the author kit from the AAAI site, replace
#   both files, and bump STYLE_YEAR / STY_FILE / BST_FILE below.
#
# This template always cleans auxiliary files first -- a stale main.aux triggers
# duplicate \bibstyle errors under aaai2026.bst.
# =============================================================================
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/latex_build.sh"

STYLE_YEAR="2026"
STY_FILE="aaai${STYLE_YEAR}.sty"
BST_FILE="aaai${STYLE_YEAR}.bst"

LATEX_NAME="AAAI template"
LATEX_SRC="${REPO_ROOT}/templates/latex/aaai"
LATEX_ALWAYS_CLEAN=1

latex_parse_args "$@"
require_file "${LATEX_SRC}/${STY_FILE}" \
    "Download the AAAI author kit from https://aaai.org/conference/aaai/aaai-${STYLE_YEAR}/aaai-${STYLE_YEAR}-author-kit/ and extract ${STY_FILE} and ${BST_FILE} into ${LATEX_SRC}"
require_texlive
latex_build
