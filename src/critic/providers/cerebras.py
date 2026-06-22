from __future__ import annotations

import importlib.util
import os

from ..config import CRITIC_CEREBRAS_MODEL, CRITIC_CEREBRAS_URL, CRITIC_TIMEOUT
from ..models import SectionLLMResult
from .base import build_user_prompt


def is_available() -> bool:
    return importlib.util.find_spec("httpx") is not None and bool(os.environ.get("CEREBRAS_API_KEY"))


class CerebrasProvider:
    name = "cerebras"

    def __init__(self, model: str = CRITIC_CEREBRAS_MODEL, base_url: str = CRITIC_CEREBRAS_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get("CEREBRAS_API_KEY", "")

    def analyze_section(self, *, rubric: str, prose: str, signals: list[str]) -> SectionLLMResult:
        import httpx  # lazy

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": rubric},
                {"role": "user", "content": build_user_prompt(prose, signals)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "section_critique", "schema": SectionLLMResult.model_json_schema()},
            },
            "temperature": 0.2,
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=CRITIC_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return SectionLLMResult.model_validate_json(content)
