#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile the IEEE conference template (templates/latex/ieee) to PDF
#
# Usage:
#   bash scripts/templates/ieee/build.sh [-c|--clean] [-q|--quiet] [-s|--src DIR]
#
# Requirements: pdflatex and bibtex in your PATH.
#   Ubuntu/Debian (WSL): sudo apt install texlive-latex-base \
#     texlive-latex-recommended texlive-publishers texlive-latex-extra \
#     texlive-fonts-recommended texlive-science
# =============================================================================
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/latex_build.sh"

LATEX_NAME="IEEE template"
LATEX_SRC="${REPO_ROOT}/templates/latex/ieee"
TEXLIVE_PKGS="texlive-latex-base texlive-latex-recommended texlive-publishers texlive-latex-extra texlive-fonts-recommended texlive-science"

latex_parse_args "$@"
require_texlive
latex_build
