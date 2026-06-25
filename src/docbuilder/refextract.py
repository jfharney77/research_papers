"""Extract a bibliography from an uploaded ``.docx`` and emit BibTeX.

Word stores bibliography data in two complementary places, tried in order:

1. **Word's built-in Sources XML** — when the author used Word's *Citations &
   Bibliography* feature, the ``.docx`` package contains a ``customXml`` part
   whose root is ``<b:Sources>``. Each ``<b:Source>`` maps cleanly onto a
   BibTeX entry.
2. **Heuristic paragraph extraction** — for manuscripts written without Word's
   citation manager, find the ``References`` heading and parse each following
   paragraph with lightweight regexes, falling back to ``@misc`` stubs.

``extract_references`` returns ``(bib_content, warning_or_None)``. The warning
is non-``None`` whenever the caller should surface a problem to the user (no
references found, or some entries could not be parsed).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from docx import Document

# Namespace used by Word's bibliography parts (Sources.xml / customXml items).
_BIB_NS = "http://schemas.openxmlformats.org/officeDocument/2006/bibliography"
_B = f"{{{_BIB_NS}}}"

# Word SourceType → BibTeX entry type.
_SOURCE_TYPE_MAP = {
    "JournalArticle": "article",
    "ArticleInAPeriodical": "article",
    "ConferenceProceedings": "inproceedings",
    "Book": "book",
    "BookSection": "incollection",
    "Report": "techreport",
}

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
# Leading "[1]" or "1." or "1)" numbering on a reference line.
_NUMBER_PREFIX_RE = re.compile(r"^\s*(?:\[\s*\d+\s*\]|\d+[.)])\s*")
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
# Author(s), "Title," Venue, Year.  — title may be quoted with " or “ ”.
_QUOTED_TITLE_RE = re.compile(r'[“"]([^”"]+)[”"]')


def extract_references(docx_path: Path) -> tuple[str, str | None]:
    """Return ``(bib_content, warning)`` for the given ``.docx``.

    Tries Word's Sources XML first, then heuristic paragraph extraction.
    """
    docx_path = Path(docx_path)

    sources = _read_sources_xml(docx_path)
    if sources:
        entries = [_source_to_bibtex(src, idx) for idx, src in enumerate(sources, start=1)]
        return "\n\n".join(entries) + "\n", None

    raw_refs = _read_reference_paragraphs(docx_path)
    if not raw_refs:
        return (
            "% No references could be extracted from the source document.\n",
            "No references could be extracted; references.bib is empty.",
        )

    entries: list[str] = []
    stub_count = 0
    for idx, raw in enumerate(raw_refs, start=1):
        entry, parsed = _heuristic_to_bibtex(raw, idx)
        entries.append(entry)
        if not parsed:
            stub_count += 1

    warning = None
    if stub_count:
        warning = (
            f"Extracted {len(raw_refs)} references; {stub_count} "
            f"{'entry' if stub_count == 1 else 'entries'} could not be parsed "
            "and are stored as @misc stubs."
        )
    return "\n\n".join(entries) + "\n", warning


# ---------------------------------------------------------------------------
# Step 1 — Word Sources XML
# ---------------------------------------------------------------------------


def _read_sources_xml(docx_path: Path) -> list:
    """Return the list of ``<b:Source>`` elements found in the package, if any."""
    from lxml import etree

    try:
        with zipfile.ZipFile(docx_path) as zf:
            names = [n for n in zf.namelist() if n.startswith("customXml/") and n.endswith(".xml")]
            for name in names:
                try:
                    root = etree.fromstring(zf.read(name))
                except etree.XMLSyntaxError:
                    continue
                if root.tag == f"{_B}Sources":
                    return list(root.findall(f"{_B}Source"))
    except (zipfile.BadZipFile, FileNotFoundError):
        return []
    return []


def _source_to_bibtex(source, index: int) -> str:
    def field(tag: str) -> str | None:
        el = source.find(f"{_B}{tag}")
        return el.text.strip() if el is not None and el.text and el.text.strip() else None

    source_type = field("SourceType") or "Misc"
    entry_type = _SOURCE_TYPE_MAP.get(source_type, "misc")
    tag = field("Tag") or f"ref{index}"
    cite_key = re.sub(r"[^A-Za-z0-9_]", "", tag) or f"ref{index}"

    fields: list[tuple[str, str]] = []
    authors = _format_authors(source)
    if authors:
        fields.append(("author", authors))
    for bib_field, word_tag in (
        ("title", "Title"),
        ("journal", "JournalName"),
        ("booktitle", "ConferenceName"),
        ("publisher", "Publisher"),
        ("year", "Year"),
        ("volume", "Volume"),
        ("number", "Issue"),
        ("pages", "Pages"),
        ("doi", "DOI"),
        ("url", "URL"),
    ):
        value = field(word_tag)
        if value:
            fields.append((bib_field, value))

    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields)
    return f"@{entry_type}{{{cite_key},\n{body}\n}}"


def _format_authors(source) -> str | None:
    """Build a BibTeX ``author`` string ("Last, First and Last, First")."""
    author_block = source.find(f"{_B}Author")
    if author_block is None:
        return None
    # <b:Author><b:Author><b:NameList><b:Person>...
    inner = author_block.find(f"{_B}Author")
    name_list = inner.find(f"{_B}NameList") if inner is not None else None
    if name_list is None:
        # Some documents use a corporate author instead of a person list.
        corp = inner.find(f"{_B}Corporate") if inner is not None else None
        if corp is not None and corp.text:
            return corp.text.strip()
        return None

    names: list[str] = []
    for person in name_list.findall(f"{_B}Person"):
        last = person.find(f"{_B}Last")
        first = person.find(f"{_B}First")
        middle = person.find(f"{_B}Middle")
        last_t = last.text.strip() if last is not None and last.text else ""
        given = " ".join(
            part.text.strip()
            for part in (first, middle)
            if part is not None and part.text and part.text.strip()
        )
        if last_t and given:
            names.append(f"{last_t}, {given}")
        elif last_t:
            names.append(last_t)
        elif given:
            names.append(given)
    return " and ".join(names) if names else None


# ---------------------------------------------------------------------------
# Step 2 — heuristic paragraph extraction
# ---------------------------------------------------------------------------


def _read_reference_paragraphs(docx_path: Path) -> list[str]:
    """Collect paragraphs under a ``References`` heading until the next heading."""
    try:
        document = Document(str(docx_path))
    except Exception:
        return []

    refs: list[str] = []
    in_references = False
    for paragraph in document.paragraphs:
        style_name = paragraph.style.name if paragraph.style else ""
        text = paragraph.text.strip()
        is_heading = style_name.startswith("Heading") or style_name == "Title"

        if not in_references:
            if is_heading and _is_references_heading(text):
                in_references = True
            continue

        # Inside the references section.
        if is_heading:
            # A new heading ends the references section.
            break
        if text:
            refs.append(text)
    return refs


def _is_references_heading(text: str) -> bool:
    normalized = re.sub(r"[^a-z]", "", text.lower())
    return normalized in {"references", "bibliography", "referencescited", "workscited"}


def _heuristic_to_bibtex(raw: str, index: int) -> tuple[str, bool]:
    """Parse one reference line. Returns ``(entry, parsed_cleanly)``."""
    text = _NUMBER_PREFIX_RE.sub("", raw).strip()
    cite_key = f"ref{index}"

    fields: list[tuple[str, str]] = []
    parsed = False

    title_match = _QUOTED_TITLE_RE.search(text)
    if title_match:
        title = title_match.group(1).strip().rstrip(".,")
        before = text[: title_match.start()].strip().rstrip(",")
        after = text[title_match.end():].strip().lstrip(",. ")
        if before:
            fields.append(("author", before))
        fields.append(("title", title))
        venue = _YEAR_RE.sub("", after).strip().strip(",. ")
        if venue:
            fields.append(("howpublished", venue))
        parsed = True

    year_match = _YEAR_RE.search(text)
    if year_match:
        fields.append(("year", year_match.group(1)))
        parsed = parsed or bool(title_match)

    doi_match = _DOI_RE.search(text)
    if doi_match:
        fields.append(("doi", doi_match.group(0)))

    if parsed:
        # Always retain the raw text in a note so nothing is lost.
        fields.append(("note", _escape_braces(raw.strip())))
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields)
        return f"@misc{{{cite_key},\n{body}\n}}", True

    # Could not parse cleanly — emit a valid @misc stub holding the raw text.
    note = _escape_braces(raw.strip())
    return f"@misc{{{cite_key},\n  note = {{{note}}}\n}}", False


def _escape_braces(text: str) -> str:
    return text.replace("{", "(").replace("}", ")")
