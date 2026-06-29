"""Task and to-do adapter.

Consumes existing Home Assistant task ecosystems (Local to-do, Todoist,
Microsoft To Do, and others) through the shared ``todo`` building block via the
``todo.get_items`` service response.
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


class TodoAdapter(HomeAssistantServiceAdapter):
    """Adapter for Home Assistant task-backed sources (``todo.get_items``)."""

    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        """Fetch open to-do items for the configured list entity."""
        source_ref = context.get(CONTEXT_SOURCE_REF)
        payload = await super().async_fetch(
            {
                **context,
                CONTEXT_SERVICE_DOMAIN: "todo",
                CONTEXT_SERVICE_NAME: "get_items",
                CONTEXT_SERVICE_DATA: {"status": ["needs_action"]},
                CONTEXT_SERVICE_TARGET: {"entity_id": source_ref} if source_ref else {},
            }
        )
        return {
            **payload,
            "source_ref": source_ref,
            "summary_limit": context.get("summary_limit", 5),
        }