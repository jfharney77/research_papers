from __future__ import annotations

from typing import Protocol

from ..models import SectionLLMResult


class CritiqueProvider(Protocol):
    name: str

    def analyze_section(
        self, *, rubric: str, prose: str, signals: list[str]
    ) -> SectionLLMResult: ...


def build_user_prompt(prose: str, signals: list[str]) -> str:
    sig = "\n".join(f"- {s}" for s in signals) or "- (none)"
    return (
        "Automatically-detected AI-genericness signals for this section:\n"
        f"{sig}\n\n"
        "Section text:\n"
        '"""\n'
        f"{prose}\n"
        '"""'
    )
