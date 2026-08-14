#!/usr/bin/env bash
# =============================================================================
# new-paper.sh -- Scaffold a new paper so papers/ and scripts/papers/ stay in sync
#
# Usage:
#   bash scripts/new-paper.sh <slug> [conference]
#
#   <slug>        Directory name for the paper, e.g. "agent-drift". Lowercase
#                 letters, digits, hyphens and underscores only.
#   [conference]  Template to seed papers/<slug>/latex from. One of the
#                 directories in templates/latex/ (default: ieee).
#
# Creates:
#   papers/<slug>/manuscript/     .docx / .md source material
#   papers/<slug>/latex/          main.tex + sections/, copied from the template
#   papers/<slug>/figures/
#   papers/<slug>/deck/
#   scripts/papers/<slug>/build.sh
#
# The generated build.sh is a wrapper over scripts/lib/latex_build.sh, so it
# inherits --clean, --quiet, --src, --help and the main.log warning report.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SLUG="${1:-}"
CONFERENCE="${2:-ieee}"

if [[ -z "${SLUG}" ]]; then
    sed -n '2,$p' "$0" | sed -n '/^#/!q;s/^# \{0,1\}//;p'
    exit 2
fi

if [[ ! "${SLUG}" =~ ^[a-z0-9_-]+$ ]]; then
    echo "[ERROR] Invalid slug: ${SLUG}"
    echo "        Use lowercase letters, digits, hyphens and underscores only."
    exit 2
fi

TEMPLATE_DIR="${REPO_ROOT}/templates/latex/${CONFERENCE}"
PAPER_DIR="${REPO_ROOT}/papers/${SLUG}"
SCRIPT_DIR="${REPO_ROOT}/scripts/papers/${SLUG}"

if [[ ! -f "${TEMPLATE_DIR}/main.tex" ]]; then
    echo "[ERROR] No such template: ${CONFERENCE}"
    echo "        Available: $(ls "${REPO_ROOT}/templates/latex" | grep -v '^_' | tr '\n' ' ')"
    exit 1
fi

if [[ -e "${PAPER_DIR}" ]]; then
    echo "[ERROR] papers/${SLUG} already exists."
    exit 1
fi

echo "[INFO] Creating papers/${SLUG} from the ${CONFERENCE} template ..."
mkdir -p "${PAPER_DIR}"/{manuscript,figures,deck}

# Copy the template skeleton, leaving build artifacts behind.
mkdir -p "${PAPER_DIR}/latex"
(cd "${TEMPLATE_DIR}" && tar --exclude='main.aux' --exclude='main.bbl' \
    --exclude='main.blg' --exclude='main.log' --exclude='main.out' \
    --exclude='main.pdf' --exclude='main.synctex.gz' -cf - .) \
    | (cd "${PAPER_DIR}/latex" && tar -xf -)

echo "[INFO] Creating scripts/papers/${SLUG}/build.sh ..."
mkdir -p "${SCRIPT_DIR}"
cat > "${SCRIPT_DIR}/build.sh" <<EOF
#!/usr/bin/env bash
# =============================================================================
# build.sh -- Compile the ${SLUG} paper (papers/${SLUG}/latex) to PDF
#
# Usage:
#   bash scripts/papers/${SLUG}/build.sh [-c|--clean] [-q|--quiet] [-s|--src DIR]
#
# Seeded from the ${CONFERENCE} template. Host TeX Live auto-install is disabled
# by default; set LATEX_AUTO_INSTALL=1 to allow it.
# =============================================================================
set -euo pipefail
source "\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/../../lib" && pwd)/latex_build.sh"

LATEX_NAME="${SLUG} paper"
LATEX_SRC="\${REPO_ROOT}/papers/${SLUG}/latex"

latex_parse_args "\$@"
require_texlive
latex_build
EOF
chmod +x "${SCRIPT_DIR}/build.sh"

# Keep the empty content dirs in git.
for d in manuscript figures deck; do touch "${PAPER_DIR}/${d}/.gitkeep"; done

echo ""
echo "Created:"
echo "  papers/${SLUG}/{manuscript,latex,figures,deck}/"
echo "  scripts/papers/${SLUG}/build.sh"
echo ""
echo "Next: drop your .docx in papers/${SLUG}/manuscript/, then run"
echo "  bash scripts/papers/${SLUG}/build.sh"
