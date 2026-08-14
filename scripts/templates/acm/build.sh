#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile the ACM conference template (templates/latex/acm) to PDF
#
# Usage:
#   bash scripts/templates/acm/build.sh [-c|--clean] [-q|--quiet] [-s|--src DIR]
#
# Style files:
#   acmart.cls and the acm*.bbx/cbx/dbx files are version-controlled in
#   templates/latex/acm/ (v2.03, Feb 2024). To update, replace them with newer
#   versions from https://ctan.org/pkg/acmart
# =============================================================================
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/latex_build.sh"

LATEX_NAME="ACM template"
LATEX_SRC="${REPO_ROOT}/templates/latex/acm"

latex_parse_args "$@"
require_file "${LATEX_SRC}/acmart.cls" \
    "Download the latest acmart from https://ctan.org/pkg/acmart and place acmart.cls plus the acm*.bbx/cbx/dbx files in ${LATEX_SRC}"
require_texlive
latex_build
