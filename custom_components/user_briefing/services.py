"""Service registration for User Briefing."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.core import ServiceResponse
from homeassistant.exceptions import ServiceValidationError

from .const import (
    CONF_CONFIG_ENTRY_ID,
    CONF_CUSTOM_TEXT_MODE,
    CONF_PROVIDER_KEY,
    CONF_SUBENTRY_ID,
    CUSTOM_TEXT_MODE_SLOT,
    DOMAIN,
    SERVICE_CLEAR_SNIPPET,
    SERVICE_DELIVER,
    SERVICE_GENERATE,
    SERVICE_PREVIEW,
    SERVICE_PUSH_SNIPPET,
    SERVICE_REFRESH_SNIPPET,
    SUBENTRY_TYPE_SNIPPET,
)
from .models import SlotEntry
from .subentries import get_config_subentry_data, iter_config_subentries

_LOGGER = logging.getLogger(__name__)

_CONFIG_ENTRY_SCHEMA = vol.Schema({vol.Required(CONF_CONFIG_ENTRY_ID): str})
_SNIPPET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): str,
        vol.Required(CONF_SUBENTRY_ID): str,
    }
)
_PUSH_SNIPPET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): str,
        vol.Required(CONF_SUBENTRY_ID): str,
        vol.Required("text"): str,
        vol.Optional("title"): str,
        vol.Optional("severity"): vol.In(["info", "warning", "critical"]),
        vol.Optional("expires_in_hours", default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=168)
        ),
    }
)


def _resolve_coordinator(hass: HomeAssistant, call: ServiceCall):
    """Resolve a coordinator from the service call."""
    domain_data = hass.data.get(DOMAIN, {})
    config_entry_id = call.data.get(CONF_CONFIG_ENTRY_ID)
    return domain_data.get(config_entry_id)


def _validate_custom_text_slot_subentry(
    hass: HomeAssistant, config_entry_id: str, subentry_id: str
) -> None:
    """Raise ServiceValidationError if the subentry is not a custom_text slot-mode subentry."""
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_config_entry_id",
        )
    for subentry in iter_config_subentries(entry, SUBENTRY_TYPE_SNIPPET):
        if getattr(subentry, "subentry_id", None) != subentry_id:
            continue
        data = get_config_subentry_data(subentry, ())
        if data.get(CONF_PROVIDER_KEY) == "custom_text" and data.get(CONF_CUSTOM_TEXT_MODE, CUSTOM_TEXT_MODE_SLOT) == CUSTOM_TEXT_MODE_SLOT:
            return
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="push_snippet_invalid_subentry",
        )
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="push_snippet_invalid_subentry",
    )


async def async_register_services(hass: HomeAssistant) -> None:
    """Register public services."""
    if hass.services.has_service(DOMAIN, SERVICE_GENERATE):
        return

    async def _handle_generate(call: ServiceCall) -> None:
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_config_entry_id",
            )
        await coordinator.async_generate()

    async def _handle_preview(call: ServiceCall) -> ServiceResponse:
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_config_entry_id",
            )
        result = await coordinator.async_preview()
        return {
            "user_key": result.user_key,
            "summary_state": result.summary_state,
            "rendered_text": result.rendered_text,
            "snippet_count": len(result.snippets),
        }

    async def _handle_deliver(call: ServiceCall) -> None:
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_config_entry_id",
            )
        result = coordinator.last_result
        if result is None:
            result = await coordinator.async_preview()
        notification_payload = result.delivery_payloads.get("notification")
        _LOGGER.debug(
            "Deliver called for %s — notification payload ready: %s; "
            "actual delivery is stubbed pending a target channel",
            call.data.get(CONF_CONFIG_ENTRY_ID),
            notification_payload is not None,
        )

    async def _handle_refresh_snippet(call: ServiceCall) -> None:
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_config_entry_id",
            )
        subentry_id = call.data.get(CONF_SUBENTRY_ID)
        await coordinator.async_generate(subentry_ids={subentry_id})

    async def _handle_push_snippet(call: ServiceCall) -> None:
        config_entry_id = call.data[CONF_CONFIG_ENTRY_ID]
        subentry_id = call.data[CONF_SUBENTRY_ID]
        _validate_custom_text_slot_subentry(hass, config_entry_id, subentry_id)

        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_config_entry_id",
            )

        expires_in_hours = float(call.data.get("expires_in_hours", 0))
        now = datetime.now(tz=timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours) if expires_in_hours > 0 else None

        coordinator.slot_store[subentry_id] = SlotEntry(
            text=call.data["text"],
            title=call.data.get("title"),
            severity=call.data.get("severity"),
            pushed_at=now,
            expires_at=expires_at,
        )

    async def _handle_clear_snippet(call: ServiceCall) -> None:
        config_entry_id = call.data[CONF_CONFIG_ENTRY_ID]
        subentry_id = call.data[CONF_SUBENTRY_ID]
        coordinator = _resolve_coordinator(hass, call)
        if coordinator is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_config_entry_id",
            )
        coordinator.slot_store.pop(subentry_id, None)

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
    hass.services.async_register(
        DOMAIN,
        SERVICE_PUSH_SNIPPET,
        _handle_push_snippet,
        schema=_PUSH_SNIPPET_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_SNIPPET,
        _handle_clear_snippet,
        schema=_SNIPPET_SCHEMA,
    )


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister public services."""
    for service_name in (
        SERVICE_GENERATE,
        SERVICE_PREVIEW,
        SERVICE_DELIVER,
        SERVICE_REFRESH_SNIPPET,
        SERVICE_PUSH_SNIPPET,
        SERVICE_CLEAR_SNIPPET,
    ):
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)