#!/usr/bin/env bash
# =============================================================================
# word_to_latex.sh -- Convert a paper's Word manuscript into per-section LaTeX
#
# Wraps the product converter (src/docbuilder) so it writes into a paper's own
# directory instead of the docserver's runtime workspace.
#
# Usage:
#   bash scripts/word_to_latex.sh                        # APIP, newest .docx
#   bash scripts/word_to_latex.sh <slug>                 # another paper
#   bash scripts/word_to_latex.sh --docx path/to/file.docx
#
# Options:
#   -d, --docx FILE   Manuscript to convert. Default: the most recently modified
#                     .docx in papers/<slug>/manuscript/.
#   -t, --template ID Conference template to convert against (default: ieee).
#   -o, --out DIR     Where to write the result. Default:
#                     papers/<slug>/latex.imported/
#   -f, --force       Write straight into papers/<slug>/latex/, moving the
#                     existing one aside to latex.bak-<timestamp>/ first.
#   -h, --help        Show this help text.
#
# BY DEFAULT THIS DOES NOT TOUCH papers/<slug>/latex/. That directory holds
# hand-edited LaTeX -- for APIP, ten section files refined well past what an
# automated pass produces. A fresh conversion is written alongside it so you can
# diff and merge deliberately. --force overwrites, keeping a timestamped backup.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SLUG="apip"
DOCX=""
TEMPLATE="ieee"
OUT=""
FORCE=0

# --- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--docx)
            [[ $# -ge 2 ]] || { echo "[ERROR] --docx requires a file"; exit 2; }
            DOCX="$2"; shift 2 ;;
        -t|--template)
            [[ $# -ge 2 ]] || { echo "[ERROR] --template requires an id"; exit 2; }
            TEMPLATE="$2"; shift 2 ;;
        -o|--out)
            [[ $# -ge 2 ]] || { echo "[ERROR] --out requires a directory"; exit 2; }
            OUT="$2"; shift 2 ;;
        -f|--force) FORCE=1; shift ;;
        -h|--help)
            sed -n '2,$p' "$0" | sed -n '/^#/!q;s/^# \{0,1\}//;p'
            exit 0 ;;
        -*) echo "[ERROR] Unknown option: $1"; echo "        Run '$0 --help' for usage."; exit 2 ;;
        *)  SLUG="$1"; shift ;;
    esac
done

PAPER_DIR="${REPO_ROOT}/papers/${SLUG}"
if [[ ! -d "${PAPER_DIR}" ]]; then
    echo "[ERROR] No such paper: papers/${SLUG}"
    echo "        Available: $(ls "${REPO_ROOT}/papers" | grep -v '\.md$' | tr '\n' ' ')"
    exit 1
fi

# --- Pick the manuscript ----------------------------------------------------
if [[ -z "${DOCX}" ]]; then
    MANUSCRIPT_DIR="${PAPER_DIR}/manuscript"
    DOCX="$(find "${MANUSCRIPT_DIR}" -maxdepth 1 -name '*.docx' -printf '%T@ %p\n' 2>/dev/null \
            | sort -rn | head -1 | cut -d' ' -f2-)"
    if [[ -z "${DOCX}" ]]; then
        echo "[ERROR] No .docx found in ${MANUSCRIPT_DIR}"
        echo "        Pass one explicitly with --docx."
        exit 1
    fi
    echo "[INFO] Using newest manuscript: ${DOCX#"${REPO_ROOT}/"}"
    echo "       (override with --docx if you meant a different version)"
fi

if [[ ! -f "${DOCX}" ]]; then
    echo "[ERROR] No such file: ${DOCX}"
    exit 1
fi
DOCX="$(realpath "${DOCX}")"

if [[ ! -f "${REPO_ROOT}/templates/latex/${TEMPLATE}/main.tex" ]]; then
    echo "[ERROR] No such template: ${TEMPLATE}"
    echo "        Available: $(ls "${REPO_ROOT}/templates/latex" | grep -v '^_' | tr '\n' ' ')"
    exit 1
fi

# --- Run the converter ------------------------------------------------------
# The converter writes into documents/<id>/ and refuses to clobber an existing
# workspace, so clear any leftover from a previous run first. documents/ is
# gitignored scratch space for the docserver -- nothing there is precious.
DOC_ID="$(basename "${DOCX}" .docx | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]\+/_/g; s/^_//; s/_$//')"
WORKSPACE="${REPO_ROOT}/documents/${DOC_ID}"
rm -rf "${WORKSPACE}"

echo "[INFO] Converting with the ${TEMPLATE} template ..."
(cd "${REPO_ROOT}" && PYTHONPATH=src uv run python -m docbuilder.cli \
    "${DOCX}" --template "${TEMPLATE}" --no-build)

CONVERTED="${WORKSPACE}/${TEMPLATE}"
if [[ ! -f "${CONVERTED}/main.tex" ]]; then
    echo "[ERROR] Converter produced no main.tex in ${CONVERTED}"
    exit 1
fi

# --- Place the result -------------------------------------------------------
if [[ ${FORCE} -eq 1 ]]; then
    DEST="${PAPER_DIR}/latex"
    if [[ -d "${DEST}" ]]; then
        BACKUP="${PAPER_DIR}/latex.bak-$(date +%Y%m%d-%H%M%S)"
        mv "${DEST}" "${BACKUP}"
        echo "[INFO] Existing LaTeX moved to ${BACKUP#"${REPO_ROOT}/"}"
    fi
else
    DEST="${OUT:-${PAPER_DIR}/latex.imported}"
    rm -rf "${DEST}"
fi

mkdir -p "${DEST}"
cp -r "${CONVERTED}/." "${DEST}/"

# The converter copies the template directory wholesale, which on a working
# checkout carries build artifacts from the last time that template was built.
rm -f "${DEST}"/main.{aux,bbl,blg,log,out,pdf,toc,synctex.gz}

REL="${DEST#"${REPO_ROOT}/"}"
echo ""
echo "============================================================"
echo " Converted: $(basename "${DOCX}")"
echo " Output   : ${REL}/"
echo "   $(find "${DEST}/sections" -name '*.tex' 2>/dev/null | wc -l) section files, $(find "${DEST}" -maxdepth 1 -name '*.tex' | wc -l) root .tex"
echo "============================================================"

if [[ ${FORCE} -eq 1 ]]; then
    echo ""
    echo "Build it:  bash scripts/papers/${SLUG}/build.sh"
else
    echo ""
    echo "This did NOT modify papers/${SLUG}/latex/. To compare:"
    echo "  diff -rq papers/${SLUG}/latex ${REL}"
    echo ""
    echo "Merge what you want by hand, or re-run with --force to replace"
    echo "papers/${SLUG}/latex/ (the old one is kept as latex.bak-<timestamp>/)."
fi
