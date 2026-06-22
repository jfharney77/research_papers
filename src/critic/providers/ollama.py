from __future__ import annotations

import importlib.util

from ..config import CRITIC_OLLAMA_MODEL, CRITIC_OLLAMA_URL, CRITIC_TIMEOUT
from ..models import SectionLLMResult
from .base import build_user_prompt


def is_available() -> bool:
    return importlib.util.find_spec("httpx") is not None


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = CRITIC_OLLAMA_MODEL, base_url: str = CRITIC_OLLAMA_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def analyze_section(self, *, rubric: str, prose: str, signals: list[str]) -> SectionLLMResult:
        import httpx  # lazy

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": rubric},
                {"role": "user", "content": build_user_prompt(prose, signals)},
            ],
            # Ollama constrains output to the JSON schema when `format` is set.
            "format": SectionLLMResult.model_json_schema(),
            "stream": False,
            "options": {"temperature": 0.2},
        }
        resp = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=CRITIC_TIMEOUT)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return SectionLLMResult.model_validate_json(content)
