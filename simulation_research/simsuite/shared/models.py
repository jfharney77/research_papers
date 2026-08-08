"""Model-access layer.

All projects call LLMs through ModelClient so a response cache can be shared
across projects (the specs claim 30-50% sweep-cost savings from this). Two
providers ship here:

- StubProvider: deterministic, seeded, zero-cost. Every demo and test runs on
  it, so the whole suite works end-to-end with no API keys.
- litellm passthrough: if `litellm` is installed and a real model name is
  given, calls go through it. Optional dependency by design.
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from pathlib import Path
from typing import Protocol


class Provider(Protocol):
    def complete(self, model: str, prompt: str, temperature: float, seed: int) -> str: ...


class StubProvider:
    """Deterministic pseudo-LLM.

    Responses are drawn from a small template pool keyed by a hash of
    (model, prompt, seed), with temperature widening the pool. Useful for
    wiring/scaling tests and for making demos reproducible.
    """

    def __init__(self, response_pool: list[str] | None = None):
        self.response_pool = response_pool or [
            "I agree with the previous points and would add that the tradeoffs matter.",
            "I disagree; the evidence points the other way.",
            "My view is shaped by my background: I lean toward caution here.",
            "This seems beneficial on balance, though costs are unevenly distributed.",
            "I remain uncertain and would want more information before deciding.",
            "Strongly in favor - the long-run gains outweigh the short-run pain.",
            "Strongly opposed - the risks fall on those least able to bear them.",
        ]

    def complete(self, model: str, prompt: str, temperature: float, seed: int) -> str:
        key = hashlib.sha256(f"{model}|{prompt}|{seed}".encode()).hexdigest()
        rng = random.Random(key)
        # Temperature widens how much of the pool is reachable.
        pool_size = max(1, min(len(self.response_pool), 1 + int(temperature * len(self.response_pool))))
        return rng.choice(self.response_pool[:pool_size])


class LiteLLMProvider:
    def complete(self, model: str, prompt: str, temperature: float, seed: int) -> str:
        import litellm  # optional dependency

        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""


class ModelClient:
    """Provider-agnostic completion client with a SQLite response cache."""

    def __init__(self, provider: Provider | None = None, cache_path: str | Path | None = None):
        self.provider = provider or StubProvider()
        self._conn: sqlite3.Connection | None = None
        if cache_path is not None:
            Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(cache_path))
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, response TEXT)"
            )
        self.calls = 0
        self.cache_hits = 0

    def _cache_key(self, model: str, prompt: str, temperature: float, seed: int) -> str:
        raw = json.dumps([model, prompt, temperature, seed])
        return hashlib.sha256(raw.encode()).hexdigest()

    def complete(self, prompt: str, model: str = "stub", temperature: float = 0.7, seed: int = 0) -> str:
        key = self._cache_key(model, prompt, temperature, seed)
        if self._conn is not None:
            row = self._conn.execute("SELECT response FROM cache WHERE key = ?", (key,)).fetchone()
            if row is not None:
                self.cache_hits += 1
                return row[0]
        self.calls += 1
        response = self.provider.complete(model, prompt, temperature, seed)
        if self._conn is not None:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache (key, response) VALUES (?, ?)", (key, response)
            )
            self._conn.commit()
        return response
