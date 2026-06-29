"""Reusable adapters for consuming existing Home Assistant integrations.

These primitives are the recommended way to pull data into a briefing provider.
Most data in Home Assistant — including everything installed via HACS — is
already exposed as entities and services, so a provider usually only needs to
point one of these adapters at an entity or service and then normalize the
result.

Two primitives cover the vast majority of cases:

- ``HomeAssistantEntityAdapter`` reads the current state and attributes of any
  entity, regardless of which integration provides it.
- ``HomeAssistantServiceAdapter`` calls any service (optionally with a response)
  for integrations that expose richer data through service responses, such as
  ``calendar.get_events``, ``weather.get_forecasts`` or ``todo.get_items``.

``StubAdapter`` remains for sources that are not wired yet.
"""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError

from ..providers.contracts import ProviderAdapter

# Context keys understood by the built-in adapters.
CONTEXT_SOURCE_REF = "source_ref"
CONTEXT_SERVICE_DOMAIN = "service_domain"
CONTEXT_SERVICE_NAME = "service_name"
CONTEXT_SERVICE_DATA = "service_data"
CONTEXT_SERVICE_TARGET = "target"

_UNAVAILABLE_STATES = ("unavailable", "unknown")


class HomeAssistantEntityAdapter(ProviderAdapter):
    """Read state and attributes from any existing Home Assistant entity.

    This is the simplest way to consume an existing integration: point it at an
    ``entity_id`` (provided in the context as ``source_ref``) and it returns the
    current state, attributes, and freshness metadata in a normalized shape.
    """

    async def async_describe_source(self, source_ref: str) -> dict[str, Any]:
        state = self.hass.states.get(source_ref)
        return {
            "entity_id": source_ref,
            "exists": state is not None,
            "friendly_name": state.attributes.get("friendly_name") if state else None,
        }

    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        entity_id = context.get(CONTEXT_SOURCE_REF)
        if not entity_id:
            return {"available": False, "entity_id": None, "items": []}

        state = self.hass.states.get(entity_id)
        if state is None:
            return {"available": False, "entity_id": entity_id, "items": []}

        return {
            "available": state.state not in _UNAVAILABLE_STATES,
            "entity_id": entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": state.last_changed.isoformat(),
            "last_updated": state.last_updated.isoformat(),
        }


class HomeAssistantServiceAdapter(ProviderAdapter):
    """Call a Home Assistant service (optionally with response) to fetch data.

    Useful for integrations that expose richer data through service responses.
    The provider supplies ``service_domain`` and ``service_name`` in the context,
    plus optional ``service_data`` and ``target``.
    """

    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        domain = context.get(CONTEXT_SERVICE_DOMAIN)
        service = context.get(CONTEXT_SERVICE_NAME)
        if not domain or not service:
            return {"available": False, "response": None}

        service_data = dict(context.get(CONTEXT_SERVICE_DATA, {}))
        target = dict(context.get(CONTEXT_SERVICE_TARGET, {}))

        try:
            response = await self.hass.services.async_call(
                domain,
                service,
                {**service_data, **target},
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError:
            return {"available": False, "response": None}

        return {"available": True, "response": response}


class StubAdapter(ProviderAdapter):
    """Placeholder adapter for sources that are not wired yet."""

    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"context": context, "items": []}