"""Offline, deterministic provider — the default when no LLM is configured.

It produces structurally valid, signal-grounded output so the whole feature
works (and is testable) without network access or credentials. Real insight
comes from the claude/ollama/cerebras providers.
"""

from __future__ import annotations

from ..heuristics import compute_heuristics
from ..models import Criticism, SectionLLMResult


class StubProvider:
    name = "stub"

    def analyze_section(self, *, rubric: str, prose: str, signals: list[str]) -> SectionLLMResult:
        report = compute_heuristics(prose)
        words = int(report.metrics.get("words", len(prose.split())))

        criticisms = [
            Criticism(
                category="style",
                issue=(
                    "Phrasing shows AI-genericness signals: "
                    + "; ".join(signals)
                    if any("no strong" not in s for s in signals)
                    else "Phrasing is mostly clean of generic markers."
                ),
                suggestion="Replace filler/transition openers with concrete, paper-specific claims.",
            ),
            Criticism(
                category="structure",
                issue=(
                    "Sentence rhythm is uniform"
                    if report.metrics.get("sentence_stdev", 99) < 5
                    else "Sentence rhythm varies acceptably"
                ),
                suggestion="Vary sentence length deliberately — mix short declaratives with longer ones.",
            ),
            Criticism(
                category="substance",
                issue=f"Section is ~{words} words; verify each claim is supported and specific.",
                suggestion="Tie general statements to concrete results, citations, or numbers.",
            ),
        ]

        tips = [
            "Cut stock phrases (e.g. 'moreover', 'it is important to note', 'leverage').",
            "Break up parallel 'rule-of-three' lists into specific, asymmetric detail.",
            "Open sentences with the subject of the claim, not a transition word.",
        ]

        return SectionLLMResult(
            criticisms=criticisms,
            ai_score_model=report.ai_score,  # mirror the heuristic when offline
            deai_tips=tips,
        )
