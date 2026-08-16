#!/usr/bin/env bash
# =============================================================================
# to_windows.sh -- Copy a built paper PDF onto the Windows filesystem
#
# WSL only. Copies papers/<slug>/latex/main.pdf to the Windows-side output
# folder so it can be opened with a normal Windows PDF viewer.
#
# Usage:
#   bash scripts/to_windows.sh                 # copy the APIP paper
#   bash scripts/to_windows.sh <slug>          # copy another paper
#   bash scripts/to_windows.sh <slug> --build  # build it first, then copy
#
# Options:
#   -b, --build       Run scripts/papers/<slug>/build.sh before copying.
#   -d, --dest DIR    Destination directory (default: the WINDOWS_OUT below,
#                     or $PAPER_OUTPUT_DIR if that is set).
#   -o, --open        Open the copied PDF in the default Windows viewer.
#   -h, --help        Show this help text.
#
# The copy is named <slug>.pdf, not main.pdf, so several papers can live in the
# output folder without clobbering each other.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WINDOWS_OUT="${PAPER_OUTPUT_DIR:-/mnt/c/Users/jfhar/paper_output}"

SLUG="apip"
BUILD=0
OPEN=0

# --- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -b|--build) BUILD=1; shift ;;
        -o|--open)  OPEN=1; shift ;;
        -d|--dest)
            [[ $# -ge 2 ]] || { echo "[ERROR] --dest requires a directory"; exit 2; }
            WINDOWS_OUT="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,$p' "$0" | sed -n '/^#/!q;s/^# \{0,1\}//;p'
            exit 0 ;;
        -*)
            echo "[ERROR] Unknown option: $1"
            echo "        Run '$0 --help' for usage."
            exit 2 ;;
        *)  SLUG="$1"; shift ;;
    esac
done

PAPER_DIR="${REPO_ROOT}/papers/${SLUG}"
PDF="${PAPER_DIR}/latex/main.pdf"

# --- Validate ---------------------------------------------------------------
if [[ ! -d "${PAPER_DIR}" ]]; then
    echo "[ERROR] No such paper: papers/${SLUG}"
    echo "        Available: $(ls "${REPO_ROOT}/papers" | grep -v '\.md$' | tr '\n' ' ')"
    exit 1
fi

if [[ ! -d /mnt/c ]]; then
    echo "[ERROR] /mnt/c not found -- this script only works under WSL."
    echo "        On another platform, copy ${PDF} wherever you need it."
    exit 1
fi

# --- Build first if asked ---------------------------------------------------
if [[ ${BUILD} -eq 1 ]]; then
    BUILD_SCRIPT="${REPO_ROOT}/scripts/papers/${SLUG}/build.sh"
    if [[ ! -f "${BUILD_SCRIPT}" ]]; then
        echo "[ERROR] No build script at scripts/papers/${SLUG}/build.sh"
        exit 1
    fi
    bash "${BUILD_SCRIPT}" --quiet
fi

if [[ ! -f "${PDF}" ]]; then
    echo "[ERROR] No PDF at: ${PDF}"
    echo "        Build it first:  bash scripts/papers/${SLUG}/build.sh"
    echo "        Or re-run this script with --build."
    exit 1
fi

# --- Copy -------------------------------------------------------------------
mkdir -p "${WINDOWS_OUT}"
DEST="${WINDOWS_OUT}/${SLUG}.pdf"

# Windows viewers hold an exclusive lock on an open PDF; cp fails mid-write and
# leaves a truncated file. Copy to a temp name and swap, so a failure leaves the
# previous copy intact.
TMP="${DEST}.tmp$$"
if ! cp "${PDF}" "${TMP}" 2>/dev/null; then
    rm -f "${TMP}"
    echo "[ERROR] Could not write to: ${WINDOWS_OUT}"
    echo "        If ${SLUG}.pdf is open in a Windows viewer, close it and retry."
    exit 1
fi
mv -f "${TMP}" "${DEST}"

SIZE="$(du -h "${DEST}" | cut -f1)"
echo "Copied → ${DEST}  (${SIZE})"

# The Windows-path form is what you paste into Explorer or a viewer.
WIN_PATH="$(printf '%s' "${DEST}" | sed 's|^/mnt/\([a-z]\)|\U\1:|; s|/|\\|g')"
echo "        ${WIN_PATH}"

if [[ ${OPEN} -eq 1 ]]; then
    if command -v wslview &>/dev/null; then
        wslview "${DEST}"
    elif command -v explorer.exe &>/dev/null; then
        explorer.exe "${WIN_PATH}" || true   # explorer.exe exits 1 even on success
    else
        echo "[WARN] Neither wslview nor explorer.exe found; open it manually."
    fi
fi
