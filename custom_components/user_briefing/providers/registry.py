"""Provider registry for User Briefing."""

from __future__ import annotations

from typing import Type

from homeassistant.core import HomeAssistant

from ..models import ProviderMetadata
from .contracts import BriefingProvider

_REGISTRY: dict[str, type[BriefingProvider]] = {}
_BUILTINS_LOADED = False


def register_provider(provider_cls: type[BriefingProvider]) -> type[BriefingProvider]:
    """Register a provider class by metadata key."""
    metadata = provider_cls.describe()
    _REGISTRY[metadata.key] = provider_cls
    return provider_cls


def list_provider_metadata() -> list[ProviderMetadata]:
    """Return sorted provider metadata."""
    return sorted(
        (provider_cls.describe() for provider_cls in _REGISTRY.values()),
        key=lambda metadata: metadata.name.lower(),
    )


def create_provider(hass: HomeAssistant, provider_key: str) -> BriefingProvider:
    """Instantiate a registered provider."""
    provider_cls = _REGISTRY[provider_key]
    return provider_cls(hass)


def ensure_builtin_providers_loaded() -> None:
    """Import built-in providers exactly once."""
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return

    from . import beach_conditions  # noqa: F401
    from . import calendar  # noqa: F401
    from . import compliment  # noqa: F401
    from . import home_status  # noqa: F401
    from . import mail_summary_stub  # noqa: F401
    from . import news_headlines  # noqa: F401
    from . import task_summary  # noqa: F401
    from . import weather_forecast  # noqa: F401
    from . import wind_conditions  # noqa: F401

    _BUILTINS_LOADED = True