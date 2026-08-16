from __future__ import annotations

import re
import unicodedata


_SANITIZE_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    lowered = normalized.lower()
    slug = _SANITIZE_RE.sub("-", lowered).strip("-")
    return slug or "section"


def snake_case(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    lowered = normalized.lower()
    snake = _SANITIZE_RE.sub("_", lowered).strip("_")
    return snake or "document"


_LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Word autocorrects plain ASCII into typographic Unicode as you type, so real
# manuscripts arrive full of smart quotes, dashes, and the U+2212 minus. pdflatex
# under inputenc/T1 rejects most of them outright ("Unicode character ... not set
# up for use with LaTeX"), which kills the build on the first pass. Map them to
# the LaTeX equivalents rather than passing them through.
_UNICODE_PUNCTUATION = {
    "‘": "`",              # ' left single quote
    "’": "'",              # ' right single quote / apostrophe
    "‚": ",",              # ‚ single low quote
    "“": "``",             # " left double quote
    "”": "''",             # " right double quote
    "„": ",,",             # „ double low quote
    "–": "--",             # – en dash
    "—": "---",            # — em dash
    "―": "---",            # ― horizontal bar
    "−": "$-$",            # − minus sign
    "…": r"\ldots{}",      # … ellipsis
    " ": "~",              #   non-breaking space
    " ": r"\,",            #   thin space
    " ": r"\,",            #   narrow no-break space
    "×": r"$\times$",      # × multiplication
    "÷": r"$\div$",        # ÷ division
    "±": r"$\pm$",         # ± plus-minus
    "≤": r"$\leq$",        # ≤
    "≥": r"$\geq$",        # ≥
    "≠": r"$\neq$",        # ≠
    "≈": r"$\approx$",     # ≈
    "°": r"$^\circ$",      # ° degree
    "†": r"\dag{}",        # † dagger
    "‡": r"\ddag{}",       # ‡ double dagger
    "§": r"\S{}",          # § section
    "¶": r"\P{}",          # ¶ pilcrow
    "•": r"$\bullet$",     # • bullet
    "®": r"\textregistered{}",
    "©": r"\copyright{}",
    "™": r"\texttrademark{}",
    "½": r"$\frac{1}{2}$",
    "→": r"$\rightarrow$",  # →
    "←": r"$\leftarrow$",   # ←
    "⇒": r"$\Rightarrow$",  # ⇒
}

_TEXT_REPLACEMENTS = {**_LATEX_SPECIALS, **_UNICODE_PUNCTUATION}


def text_to_latex(text: str) -> str:
    escaped = []
    for ch in text:
        escaped.append(_TEXT_REPLACEMENTS.get(ch, ch))
    return "".join(escaped)
