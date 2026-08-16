#!/usr/bin/env bash
# =============================================================================
# latex_to_word.sh -- Convert a paper's LaTeX back into a Word document
#
# The reverse of scripts/word_to_latex.sh. Uses pandoc to turn
# papers/<slug>/latex/main.tex into a .docx, resolving \input{} section files
# and \cite{} keys against references.bib along the way.
#
# Usage:
#   bash scripts/latex_to_word.sh                    # APIP → papers/apip/manuscript/
#   bash scripts/latex_to_word.sh <slug>             # another paper
#   bash scripts/latex_to_word.sh --out draft.docx   # explicit output path
#
# Options:
#   -o, --out FILE    Output .docx path. Default:
#                     papers/<slug>/manuscript/<slug>_from_latex.docx
#   -s, --src DIR     LaTeX directory to convert (default: papers/<slug>/latex).
#   -r, --reference F Word file whose styles the output should inherit. Default:
#                     templates/word/reference.docx if it exists.
#       --windows     Also copy the result to the Windows output folder
#                     (see scripts/to_windows.sh).
#   -h, --help        Show this help text.
#
# Requires pandoc. Install with:  sudo apt install pandoc
# Set LATEX_AUTO_INSTALL=1 to let this script apt-get it for you.
#
# A round trip is lossy in both directions. Pandoc renders the document body
# faithfully but drops LaTeX-specific formatting the .docx has no equivalent for
# (custom macros, IEEEtran title-block markup, precise float placement). Treat
# the output as a review/comment copy for collaborators, not as the source of
# truth -- that stays in papers/<slug>/latex/.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SLUG="apip"
OUT=""
SRC=""
REFERENCE=""
TO_WINDOWS=0

# --- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--out)
            [[ $# -ge 2 ]] || { echo "[ERROR] --out requires a file"; exit 2; }
            OUT="$2"; shift 2 ;;
        -s|--src)
            [[ $# -ge 2 ]] || { echo "[ERROR] --src requires a directory"; exit 2; }
            SRC="$(realpath "$2")"; shift 2 ;;
        -r|--reference)
            [[ $# -ge 2 ]] || { echo "[ERROR] --reference requires a file"; exit 2; }
            REFERENCE="$(realpath "$2")"; shift 2 ;;
        --windows) TO_WINDOWS=1; shift ;;
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

SRC="${SRC:-${PAPER_DIR}/latex}"
if [[ ! -f "${SRC}/main.tex" ]]; then
    echo "[ERROR] Cannot find main.tex in: ${SRC}"
    exit 1
fi

OUT="${OUT:-${PAPER_DIR}/manuscript/${SLUG}_from_latex.docx}"

# --- Require pandoc ---------------------------------------------------------
if ! command -v pandoc &>/dev/null; then
    if [[ "${LATEX_AUTO_INSTALL:-0}" != "1" ]]; then
        echo "[ERROR] pandoc not found -- it is what does the LaTeX → Word conversion."
        echo "        Install it:  sudo apt install pandoc"
        echo "        Or re-run with LATEX_AUTO_INSTALL=1 to install it here."
        exit 1
    fi
    if ! command -v apt-get &>/dev/null; then
        echo "[ERROR] apt-get not found. Install pandoc manually: https://pandoc.org/installing.html"
        exit 1
    fi
    echo "[INFO] Installing pandoc via apt-get (requires sudo) ..."
    sudo apt-get update -qq
    sudo apt-get install -y pandoc
    command -v pandoc &>/dev/null || { echo "[ERROR] pandoc still not found after install."; exit 1; }
fi

# --- Reference styles -------------------------------------------------------
if [[ -z "${REFERENCE}" && -f "${REPO_ROOT}/templates/word/reference.docx" ]]; then
    REFERENCE="${REPO_ROOT}/templates/word/reference.docx"
fi

PANDOC_ARGS=(
    main.tex
    --from=latex
    --to=docx
    --output="${OUT}"
    # Resolve \input{sections/...} and \includegraphics against the source dir.
    --resource-path=".:sections:figures:../figures:../../templates/assets/figures"
    --standalone
)

# Render \cite{} keys into real text rather than dropping them, when there is a
# bibliography with actual entries to render from.
if [[ -f "${SRC}/references.bib" ]] && grep -q '@' "${SRC}/references.bib"; then
    PANDOC_ARGS+=(--citeproc --bibliography=references.bib)
else
    echo "[WARN] No bibliography entries in ${SRC#"${REPO_ROOT}/"}/references.bib --"
    echo "       \\cite{} keys will render as-is."
fi

[[ -n "${REFERENCE}" ]] && PANDOC_ARGS+=(--reference-doc="${REFERENCE}")

# --- Convert ----------------------------------------------------------------
mkdir -p "$(dirname "${OUT}")"

echo ""
echo "============================================================"
echo " Converting ${SLUG} LaTeX → Word"
echo " Source : ${SRC#"${REPO_ROOT}/"}/main.tex"
echo "============================================================"
echo ""

pushd "${SRC}" > /dev/null
pandoc "${PANDOC_ARGS[@]}"
popd > /dev/null

SIZE="$(du -h "${OUT}" | cut -f1)"
echo "Wrote → ${OUT#"${REPO_ROOT}/"}  (${SIZE})"
echo ""
echo "Round trips are lossy: this is a review copy for collaborators."
echo "The source of truth stays in papers/${SLUG}/latex/."

if [[ ${TO_WINDOWS} -eq 1 ]]; then
    WINDOWS_OUT="${PAPER_OUTPUT_DIR:-/mnt/c/Users/jfhar/paper_output}"
    if [[ -d /mnt/c ]]; then
        mkdir -p "${WINDOWS_OUT}"
        cp "${OUT}" "${WINDOWS_OUT}/$(basename "${OUT}")"
        echo ""
        echo "Copied → ${WINDOWS_OUT}/$(basename "${OUT}")"
    else
        echo "[WARN] /mnt/c not found; skipping the Windows copy."
    fi
fi
