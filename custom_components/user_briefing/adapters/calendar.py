"""Calendar adapter.

Consumes the existing Home Assistant ``calendar`` integration via the
``calendar.get_events`` service response.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .base import (
    CONTEXT_SERVICE_DATA,
    CONTEXT_SERVICE_DOMAIN,
    CONTEXT_SERVICE_NAME,
    CONTEXT_SERVICE_TARGET,
    CONTEXT_SOURCE_REF,
    HomeAssistantServiceAdapter,
)


class CalendarAdapter(HomeAssistantServiceAdapter):
    """Adapter for calendar-backed sources (``calendar.get_events``)."""

    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        """Fetch upcoming calendar events for the configured entity."""
        source_ref = context.get(CONTEXT_SOURCE_REF)
        payload = await super().async_fetch(
            {
                **context,
                CONTEXT_SERVICE_DOMAIN: "calendar",
                CONTEXT_SERVICE_NAME: "get_events",
                CONTEXT_SERVICE_DATA: {
                    "start_date_time": dt_util.now(),
                    "duration": timedelta(days=1),
                },
                CONTEXT_SERVICE_TARGET: {"entity_id": source_ref} if source_ref else {},
            }
        )
        return {
            **payload,
            "source_ref": source_ref,
            "summary_limit": context.get("summary_limit", 3),
        }