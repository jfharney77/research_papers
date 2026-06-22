"""Deterministic, network-free signals for how 'generically AI' prose reads.

Each sub-metric maps to 0-100 (higher = more AI-like); the report blends them
into ``ai_score`` and emits human-readable ``signals`` reused by the UI and as
grounding context for the LLM provider.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

FILLER_PHRASES = [
    "delve", "moreover", "furthermore", "it is important to note",
    "it is worth noting", "plays a crucial role", "plays a vital role",
    "rich tapestry", "navigating the landscape", "underscores the importance",
    "leverage", "robust", "seamless", "seamlessly", "comprehensive",
    "in the realm of", "a testament to", "paradigm shift", "ever-evolving",
    "intricate", "pivotal", "notably", "significantly", "in today's world",
    "cutting-edge", "holistic", "synergy", "myriad",
]

# Sentences that open with these read as formulaic when frequent.
TRANSITION_OPENERS = {
    "however", "moreover", "furthermore", "additionally", "consequently",
    "therefore", "thus", "indeed", "notably", "importantly", "overall",
    "in conclusion", "in summary", "first", "firstly", "second", "secondly",
    "finally", "this", "these", "such",
}

_WORD_RE = re.compile(r"[A-Za-z']+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TRICOLON_RE = re.compile(r",\s+[^,]+,\s+and\s+", re.IGNORECASE)


@dataclass
class HeuristicReport:
    ai_score: int
    signals: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


def _clamp(x: float) -> int:
    return int(max(0, min(100, round(x))))


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def _sentences(text: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(text.strip()) if s.strip()]


def compute_heuristics(prose: str) -> HeuristicReport:
    words = _words(prose)
    n_words = len(words)
    if n_words < 25:
        return HeuristicReport(ai_score=0, signals=["section too short to assess reliably"])

    sentences = _sentences(prose)
    lower = prose.lower()

    # 1. Stock/filler phrases (per 1000 words)
    filler_hits = sum(lower.count(p) for p in FILLER_PHRASES)
    filler_rate = filler_hits / n_words * 1000
    filler_score = _clamp(filler_rate * 11)

    # 2. Burstiness — low sentence-length variance reads as AI-like
    lengths = [len(_words(s)) for s in sentences] or [n_words]
    stdev = statistics.pstdev(lengths) if len(lengths) >= 3 else 12.0
    burst_score = _clamp(100 - stdev * 8)

    # 3. Uniform openings / transition density
    openers = [(_words(s)[:1] or [""])[0].lower() for s in sentences]
    trans_open = sum(1 for o in openers if o in TRANSITION_OPENERS)
    trans_rate = trans_open / len(sentences) if sentences else 0.0
    trans_score = _clamp(trans_rate * 220)

    # 4. Tricolon ("X, Y, and Z") rate per 1000 words
    tricolons = len(_TRICOLON_RE.findall(prose))
    tricolon_score = _clamp(tricolons / n_words * 1000 * 25)

    # 5. Em-dash density per 1000 words
    emdashes = prose.count("—") + prose.count(" -- ")
    emdash_score = _clamp(emdashes / n_words * 1000 * 12)

    # Blend — filler + burstiness dominate.
    ai_score = _clamp(
        0.34 * filler_score
        + 0.30 * burst_score
        + 0.16 * trans_score
        + 0.10 * tricolon_score
        + 0.10 * emdash_score
    )

    signals: list[str] = []
    if filler_hits:
        signals.append(f"{filler_hits} stock/filler phrase(s) (~{filler_rate:.0f}/1k words)")
    if len(lengths) >= 3 and stdev < 5:
        signals.append(f"low sentence-length variance (σ={stdev:.1f})")
    if trans_open >= 2:
        signals.append(f"{trans_open} sentences open with a transition/filler word")
    if tricolons:
        signals.append(f"{tricolons} 'rule-of-three' construction(s)")
    if emdashes >= 2:
        signals.append(f"{emdashes} em-dash(es)")
    if not signals:
        signals.append("no strong AI-genericness signals detected")

    return HeuristicReport(
        ai_score=ai_score,
        signals=signals,
        metrics={
            "filler_score": filler_score,
            "burstiness_score": burst_score,
            "transition_score": trans_score,
            "tricolon_score": tricolon_score,
            "emdash_score": emdash_score,
            "sentence_stdev": round(stdev, 2),
            "words": n_words,
        },
    )
