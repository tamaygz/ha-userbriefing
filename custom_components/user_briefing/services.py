"""Service registration for User Briefing."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.core import ServiceResponse

from .const import (
    CONF_CONFIG_ENTRY_ID,
    CONF_SUBENTRY_ID,
    DOMAIN,
    SERVICE_DELIVER,
    SERVICE_GENERATE,
    SERVICE_PREVIEW,
    SERVICE_REFRESH_SNIPPET,
)

_LOGGER = logging.getLogger(__name__)

_CONFIG_ENTRY_SCHEMA = vol.Schema({vol.Required(CONF_CONFIG_ENTRY_ID): str})
_SNIPPET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): str,
        vol.Required(CONF_SUBENTRY_ID): str,
    }
)


def _resolve_coordinator(hass: HomeAssistant, call: ServiceCall):
    """Resolve a coordinator from the service call."""
    domain_data = hass.data.get(DOMAIN, {})
    config_entry_id = call.data.get(CONF_CONFIG_ENTRY_ID)
    return domain_data.get(config_entry_id)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register public services."""
    if hass.services.has_service(DOMAIN, SERVICE_GENERATE):
        return

    async def _handle_generate(call: ServiceCall) -> None:
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise vol.Invalid("Unknown config_entry_id")
        await coordinator.async_generate()

    async def _handle_preview(call: ServiceCall) -> ServiceResponse:
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise vol.Invalid("Unknown config_entry_id")
        result = await coordinator.async_preview()
        return {
            "user_key": result.user_key,
            "summary_state": result.summary_state,
            "rendered_text": result.rendered_text,
            "snippet_count": len(result.snippets),
        }

    async def _handle_deliver(call: ServiceCall) -> None:
        _LOGGER.debug("Deliver called with %s", call.data)

    async def _handle_refresh_snippet(call: ServiceCall) -> None:
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise vol.Invalid("Unknown config_entry_id")
        subentry_id = call.data.get(CONF_SUBENTRY_ID)
        await coordinator.async_generate(subentry_ids={subentry_id})

    hass.services.async_register(DOMAIN, SERVICE_GENERATE, _handle_generate, schema=_CONFIG_ENTRY_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_PREVIEW,
        _handle_preview,
        schema=_CONFIG_ENTRY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, SERVICE_DELIVER, _handle_deliver, schema=_CONFIG_ENTRY_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_SNIPPET,
        _handle_refresh_snippet,
        schema=_SNIPPET_SCHEMA,
    )


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister public services."""
    for service_name in (
        SERVICE_GENERATE,
        SERVICE_PREVIEW,
        SERVICE_DELIVER,
        SERVICE_REFRESH_SNIPPET,
    ):
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)