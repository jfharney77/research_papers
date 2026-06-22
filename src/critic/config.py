from __future__ import annotations

import os

# Active provider: stub (default, offline) | claude | ollama | cerebras
CRITIC_PROVIDER = os.environ.get("CRITIC_PROVIDER", "stub").strip().lower()

# Claude
CRITIC_CLAUDE_MODEL = os.environ.get("CRITIC_CLAUDE_MODEL", "claude-opus-4-8")

# Ollama (Windows host reached via the WSL gateway IP, not localhost)
CRITIC_OLLAMA_URL = os.environ.get(
    "CRITIC_OLLAMA_URL", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
)
CRITIC_OLLAMA_MODEL = os.environ.get("CRITIC_OLLAMA_MODEL", "qwen2.5")

# Cerebras (OpenAI-compatible)
CRITIC_CEREBRAS_URL = os.environ.get("CRITIC_CEREBRAS_URL", "https://api.cerebras.ai/v1")
CRITIC_CEREBRAS_MODEL = os.environ.get("CRITIC_CEREBRAS_MODEL", "gpt-oss-120b")

# Per-section LLM call budget (seconds)
CRITIC_TIMEOUT = int(os.environ.get("CRITIC_TIMEOUT", "120") or 120)

RUBRIC = """\
You are a rigorous peer reviewer and writing critic for academic papers.
For the single section of text you are given, return JSON with:
  - exactly 3 "criticisms", each a distinct, specific, actionable point with a
    category (substance | clarity | structure | rigor | style), the "issue",
    and a concrete "suggestion";
  - "ai_score_model": an integer 0-100 estimating how much the prose reads like
    generic, AI-generated writing (0 = distinctly human/varied, 100 = boilerplate
    LLM prose). You are given automatically-detected signals; weigh them.
  - "deai_tips": 2-4 concrete rewrite tips to make the sentence structures less
    "AI-like", grounded in the specific signals and the actual text.
Be specific to THIS section. Do not invent facts. This is a writing-quality
assessment, not a claim about authorship."""
