"""Weather adapter.

Consumes the existing Home Assistant ``weather`` integration via the
``weather.get_forecasts`` service response, with entity state as a fallback.
"""

from __future__ import annotations

from typing import Any

from .base import (
    CONTEXT_SERVICE_DATA,
    CONTEXT_SERVICE_DOMAIN,
    CONTEXT_SERVICE_NAME,
    CONTEXT_SERVICE_TARGET,
    CONTEXT_SOURCE_REF,
    HomeAssistantServiceAdapter,
)


class WeatherAdapter(HomeAssistantServiceAdapter):
    """Adapter for weather-backed sources (``weather.get_forecasts``)."""

    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        """Fetch daily forecasts for the configured weather entity."""
        source_ref = context.get(CONTEXT_SOURCE_REF)
        payload = await super().async_fetch(
            {
                **context,
                CONTEXT_SERVICE_DOMAIN: "weather",
                CONTEXT_SERVICE_NAME: "get_forecasts",
                CONTEXT_SERVICE_DATA: {"type": "daily"},
                CONTEXT_SERVICE_TARGET: {"entity_id": source_ref} if source_ref else {},
            }
        )
        return {
            **payload,
            "source_ref": source_ref,
            "summary_limit": context.get("summary_limit", 3),
        }