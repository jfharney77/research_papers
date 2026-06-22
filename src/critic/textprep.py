"""Turn LaTeX / docx / PDF into plain prose sections for the critic."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

_COMMENT = re.compile(r"(?<!\\)%.*")
_ENV = re.compile(r"\\(?:begin|end)\{[^}]*\}")
_MATH = re.compile(r"\$[^$]*\$")
_HEADING = re.compile(r"\\(?:section|subsection|subsubsection|paragraph)\*?\{([^}]*)\}")
_DROP_CMD = re.compile(r"\\(?:cite|ref|eqref|label|includegraphics|input|usepackage)\s*(?:\[[^\]]*\])?\{[^}]*\}")
_ANY_CMD = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?")
_WS = re.compile(r"\s+")


@dataclass
class RawSection:
    title: str
    slug: str
    text: str


def strip_latex(tex: str) -> str:
    """Reduce a LaTeX fragment to readable prose."""
    s = _COMMENT.sub("", tex)
    s = _ENV.sub(" ", s)
    s = _MATH.sub(" ", s)
    s = _HEADING.sub(r"\1. ", s)
    s = _DROP_CMD.sub(" ", s)
    s = _ANY_CMD.sub(" ", s)
    s = s.replace("{", " ").replace("}", " ").replace("\\", " ")
    s = s.replace("~", " ").replace("&", " ")
    return _WS.sub(" ", s).strip()


def _slug(text: str, idx: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or f"section-{idx}"


def sections_from_docx(data: bytes) -> list[RawSection]:
    from docx import Document  # lazy: only needed for ad-hoc docx

    doc = Document(io.BytesIO(data))
    sections: list[RawSection] = []
    title = "Introduction"
    buf: list[str] = []
    order = 1

    def flush() -> None:
        nonlocal order
        text = "\n".join(buf).strip()
        if text:
            sections.append(RawSection(title=title, slug=_slug(title, order), text=text))
            order += 1

    for para in doc.paragraphs:
        style = para.style.name if para.style else ""
        text = para.text.strip()
        if style.startswith("Heading"):
            flush()
            buf = []
            title = text or f"Section {order}"
        elif text:
            buf.append(text)
    flush()

    if not sections:  # no headings — treat the whole doc as one section
        whole = "\n".join(p.text for p in doc.paragraphs).strip()
        if whole:
            sections.append(RawSection(title="Document", slug="document", text=whole))
    return sections


def sections_from_pdf(data: bytes) -> list[RawSection]:
    from pypdf import PdfReader  # lazy: only needed for ad-hoc pdf

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    return [RawSection(title="Document", slug="document", text=text)] if text else []


def sections_from_upload(filename: str, data: bytes) -> list[RawSection]:
    name = (filename or "").lower()
    if name.endswith(".docx"):
        return sections_from_docx(data)
    if name.endswith(".pdf"):
        return sections_from_pdf(data)
    raise ValueError("Only .pdf and .docx uploads are supported")
