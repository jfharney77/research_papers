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


def text_to_latex(text: str) -> str:
    escaped = []
    for ch in text:
        escaped.append(_LATEX_SPECIALS.get(ch, ch))
    return "".join(escaped)
