"""Unit tests for ``_rewrite_main`` (no LaTeX toolchain required).

These cover the structural invariants from CRITIQUE_SPEC_3: the rewritten
``main.tex`` must contain no template placeholder ``\\input{}`` calls, must list
each converted section exactly once before the bibliography, and must carry the
real manuscript title instead of "Paper Title Goes Here".
"""

from __future__ import annotations

import re

import pytest

from docbuilder.converter import _copy_template, _rewrite_main
from docbuilder.models import SectionEntry

# A minimal synthetic main.tex mirroring the real templates: placeholder title,
# placeholder section \input lines, and a bibliography after the body.
FIXTURE_MAIN = r"""\documentclass{article}
\begin{document}
\title{Paper Title Goes Here}
\maketitle
\input{sections/abstract}
\input{sections/introduction}
\input{sections/related_work}
\input{sections/figures}
\input{sections/conclusion}
\bibliographystyle{IEEEtran}
\bibliography{references}
\end{document}
"""


def _section(slug: str, order: int) -> SectionEntry:
    return SectionEntry(
        section_id=slug,
        title=slug.replace("-", " ").title(),
        level=1,
        slug=slug,
        latex_path=f"sections/{slug}.tex",
        order=order,
    )


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ieee"
    ws.mkdir()
    (ws / "main.tex").write_text(FIXTURE_MAIN)
    return ws


@pytest.fixture
def sections():
    return [
        _section("methodology", 2),
        _section("background", 1),
        _section("results", 3),
    ]


def test_no_placeholder_section_inputs(workspace, sections):
    _rewrite_main(workspace, sections, title="My Real Title")
    out = (workspace / "main.tex").read_text()
    for placeholder in ("abstract", "introduction", "related_work", "figures", "conclusion"):
        assert f"\\input{{sections/{placeholder}}}" not in out


def test_each_section_appears_once_in_order(workspace, sections):
    _rewrite_main(workspace, sections, title="My Real Title")
    out = (workspace / "main.tex").read_text()
    found = re.findall(r"\\input\{sections/([\w-]+)\}", out)
    assert found == ["background", "methodology", "results"]


def test_sections_precede_bibliography(workspace, sections):
    _rewrite_main(workspace, sections, title="My Real Title")
    out = (workspace / "main.tex").read_text()
    bib_pos = out.index("\\bibliography{references}")
    for entry in sections:
        assert out.index(f"\\input{{sections/{entry.slug}}}") < bib_pos


def test_title_is_substituted(workspace, sections):
    _rewrite_main(workspace, sections, title="My Real Title")
    out = (workspace / "main.tex").read_text()
    assert "\\title{My Real Title}" in out
    assert "Paper Title Goes Here" not in out


def test_title_is_latex_escaped(workspace, sections):
    _rewrite_main(workspace, sections, title="Cost & Scope of AI")
    out = (workspace / "main.tex").read_text()
    assert "\\title{Cost \\& Scope of AI}" in out


def test_no_bibliography_appends_at_end(tmp_path, sections):
    ws = tmp_path / "plain"
    ws.mkdir()
    (ws / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "\\title{Paper Title Goes Here}\n\\input{sections/abstract}\n"
        "\\end{document}\n"
    )
    _rewrite_main(ws, sections, title="No Bib")
    out = (ws / "main.tex").read_text()
    assert "\\input{sections/abstract}" not in out
    for entry in sections:
        assert f"\\input{{sections/{entry.slug}}}" in out
    # All section inputs appear before \end{document}.
    end_pos = out.index("\\end{document}")
    for entry in sections:
        assert out.index(f"\\input{{sections/{entry.slug}}}") < end_pos


def test_copy_template_drops_placeholder_sections(tmp_path):
    src = tmp_path / "tmpl"
    (src / "sections").mkdir(parents=True)
    (src / "main.tex").write_text("\\documentclass{article}\n")
    (src / "sections" / "abstract.tex").write_text("Lorem ipsum")
    (src / "sections" / "introduction.tex").write_text("Lorem ipsum")

    dest = tmp_path / "ws"
    _copy_template(src, dest)

    assert (dest / "main.tex").exists()
    assert (dest / "sections").is_dir()
    assert list((dest / "sections").glob("*.tex")) == []
