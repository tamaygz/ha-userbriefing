"""Custom text provider — slot-mode and entity-mode push content injection."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector

from ..adapters.base import HomeAssistantEntityAdapter
from ..const import (
    CONF_CUSTOM_TEXT_DEFAULT_TEXT,
    CONF_CUSTOM_TEXT_MODE,
    CONF_CUSTOM_TEXT_SLOT_LABEL,
    CONF_SOURCE_REF,
    CONF_SOURCE_TYPE,
    CUSTOM_TEXT_MODE_ENTITY,
    CUSTOM_TEXT_MODE_SLOT,
)
from ..models import AlertItem, ProviderMetadata, SnippetResult
from .contracts import BriefingProvider, ProviderAdapter
from .registry import register_provider

_ENTITY_DOMAINS = ["input_text", "sensor", "template"]


@register_provider
class CustomTextProvider(BriefingProvider):
    """Push-based or entity-watching custom text provider."""

    @classmethod
    def describe(cls) -> ProviderMetadata:
        return ProviderMetadata(
            key="custom_text",
            name="Custom text",
            version="0.1.0",
            provider_api_version=1,
            supports_multiple_instances=True,
            supports_preview=True,
            supports_alerts=True,
            supports_required_priority=True,
            default_order_group="general",
        )

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(CONF_CUSTOM_TEXT_SLOT_LABEL, default=""): selector.TextSelector(),
                vol.Required(CONF_CUSTOM_TEXT_MODE, default=CUSTOM_TEXT_MODE_SLOT): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=CUSTOM_TEXT_MODE_SLOT, label="Push service (automation-driven)"),
                            selector.SelectOptionDict(value=CUSTOM_TEXT_MODE_ENTITY, label="Entity watcher"),
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

    def build_entity_schema(self) -> vol.Schema:
        """Return the schema for the entity-mode source step."""
        return vol.Schema(
            {
                vol.Required(CONF_SOURCE_REF): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=_ENTITY_DOMAINS)
                ),
            }
        )

    def build_options_schema(self) -> vol.Schema | None:
        return vol.Schema(
            {
                vol.Optional(CONF_CUSTOM_TEXT_DEFAULT_TEXT, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )

    def validate_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        config: dict[str, Any] = {
            CONF_CUSTOM_TEXT_MODE: user_input.get(CONF_CUSTOM_TEXT_MODE, CUSTOM_TEXT_MODE_SLOT),
            CONF_CUSTOM_TEXT_SLOT_LABEL: user_input.get(CONF_CUSTOM_TEXT_SLOT_LABEL, ""),
        }
        source_ref = user_input.get(CONF_SOURCE_REF)
        if source_ref:
            config[CONF_SOURCE_REF] = source_ref
            config[CONF_SOURCE_TYPE] = "entity"
        return config

    def validate_reconfigure_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return self.validate_config(user_input)

    def get_adapter(self) -> ProviderAdapter | None:
        return None

    def get_instance_title(self, config: dict[str, Any]) -> str:
        label = config.get(CONF_CUSTOM_TEXT_SLOT_LABEL)
        if label:
            return str(label)
        return self.describe().name

    def get_instance_unique_key(self, config: dict[str, Any]) -> str | None:
        source_ref = config.get(CONF_SOURCE_REF)
        if source_ref:
            return str(source_ref)
        return None

    async def async_collect(self, config: dict[str, Any]) -> dict[str, Any]:
        mode = config.get(CONF_CUSTOM_TEXT_MODE, CUSTOM_TEXT_MODE_SLOT)

        if mode == CUSTOM_TEXT_MODE_ENTITY:
            source_ref = config.get(CONF_SOURCE_REF)
            if not source_ref:
                return {"empty": True}
            adapter = HomeAssistantEntityAdapter(self.hass)
            result = await adapter.async_fetch({"source_ref": source_ref})
            state = result.get("state", "")
            if not result.get("available") or not state or state in ("unavailable", "unknown", ""):
                return {"empty": True}
            return {"text": state, "title": None, "severity": None}

        # Slot mode — coordinator must inject the slot entry into config before calling.
        slot_entry = config.get("_slot_entry")
        if slot_entry is None:
            default_text = config.get(CONF_CUSTOM_TEXT_DEFAULT_TEXT, "")
            if not default_text:
                return {"empty": True}
            return {"text": default_text, "title": None, "severity": None}

        return {
            "text": slot_entry.text,
            "title": slot_entry.title,
            "severity": slot_entry.severity,
        }

    def normalize(self, payload: dict[str, Any], instance_id: str) -> SnippetResult:
        if payload.get("empty"):
            return SnippetResult(
                provider_key=self.describe().key,
                instance_id=instance_id,
                status="skipped",
                priority="optional",
                title=self.describe().name,
                text="",
                scenario="empty",
            )

        text = str(payload.get("text") or "")
        title = str(payload.get("title") or self.describe().name)
        severity = payload.get("severity")

        alerts: list[AlertItem] = []
        if severity in ("info", "warning", "critical"):
            alerts.append(
                AlertItem(
                    alert_key=f"{instance_id}:custom_text",
                    provider_key=self.describe().key,
                    severity=severity,
                    title=title,
                    text=text,
                )
            )

        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="ok",
            priority="optional",
            title=title,
            text=text,
            scenario="custom_text",
            alerts=alerts,
        )
