from __future__ import annotations

import importlib.util

from ..config import CRITIC_CLAUDE_MODEL
from ..models import SectionLLMResult
from .base import build_user_prompt


def is_available() -> bool:
    return importlib.util.find_spec("anthropic") is not None


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str = CRITIC_CLAUDE_MODEL):
        import anthropic  # lazy

        self.model = model
        self._client = anthropic.Anthropic()

    def analyze_section(self, *, rubric: str, prose: str, signals: list[str]) -> SectionLLMResult:
        # Structured output validated against the Pydantic schema; rubric cached.
        resp = self._client.messages.parse(
            model=self.model,
            max_tokens=4000,
            system=[{"type": "text", "text": rubric, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": build_user_prompt(prose, signals)}],
            output_format=SectionLLMResult,
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            raise RuntimeError("Claude declined to analyze this section")
        return resp.parsed_output
