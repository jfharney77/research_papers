#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile the APIP paper (papers/apip/latex) to PDF
#
# "Your Agent is Underperforming: The Case for Agent Performance Improvement
# Plans", converted from papers/apip/manuscript/APIP_Paper_v8_tracked.docx into
# the IEEE conference style.
#
# Usage:
#   bash scripts/papers/apip/build.sh [-c|--clean] [-q|--quiet] [-s|--src DIR]
#
# IEEEtran.cls and IEEEtran.bst are vendored in papers/apip/latex/, so no IEEE
# TeX Live package is required -- only pdflatex and bibtex.
#
# Host auto-install is disabled by default; set LATEX_AUTO_INSTALL=1 to let the
# build apt-get TeX Live for you.
# =============================================================================
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/latex_build.sh"

LATEX_NAME="APIP paper"
LATEX_SRC="${REPO_ROOT}/papers/apip/latex"

latex_parse_args "$@"
require_texlive
latex_build
