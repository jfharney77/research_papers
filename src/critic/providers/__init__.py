"""Provider factory + availability reporting."""

from __future__ import annotations

import logging

from ..config import CRITIC_PROVIDER
from ..models import ProviderInfo, ProviderListResponse
from .base import CritiqueProvider
from .stub import StubProvider

logger = logging.getLogger(__name__)

_ALL = ["stub", "claude", "ollama", "cerebras"]


def _availability() -> dict[str, bool]:
    from . import cerebras, claude, ollama

    return {
        "stub": True,
        "claude": claude.is_available(),
        "ollama": ollama.is_available(),
        "cerebras": cerebras.is_available(),
    }


def get_provider(name: str | None = None) -> CritiqueProvider:
    """Return the configured provider, falling back to the stub on any problem."""
    name = (name or CRITIC_PROVIDER or "stub").lower()
    try:
        if name == "claude":
            from .claude import ClaudeProvider

            return ClaudeProvider()
        if name == "ollama":
            from .ollama import OllamaProvider

            return OllamaProvider()
        if name == "cerebras":
            from .cerebras import CerebrasProvider

            return CerebrasProvider()
    except Exception:  # missing SDK / bad config — degrade rather than 500
        logger.warning("Critic provider %r unavailable; using the offline stub.", name, exc_info=True)
    return StubProvider()


def active_provider_name() -> str:
    return get_provider().name


def available_providers() -> ProviderListResponse:
    avail = _availability()
    active = active_provider_name()
    return ProviderListResponse(
        providers=[ProviderInfo(id=p, available=avail.get(p, False), active=p == active) for p in _ALL],
        active=active,
    )
