"""Shared stub implementation helpers for built-in providers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector

from ..const import CONF_SOURCE_REF, CONF_SOURCE_TYPE
from ..models import DashboardFragment, ProviderMetadata, SnippetResult
from .contracts import BriefingProvider


class StubBriefingProvider(BriefingProvider):
    """Convenience base class for scaffolded providers."""

    provider_key = "stub"
    provider_name = "Stub Provider"
    supports_multiple_instances = True
    supports_actions = False
    supports_deep_link = False
    supports_dashboard_card = True
    supports_alerts = False
    source_type = "entity"
    summary_limit_default: int | None = 3

    @classmethod
    def describe(cls) -> ProviderMetadata:
        return ProviderMetadata(
            key=cls.provider_key,
            name=cls.provider_name,
            version="0.1.0",
            provider_api_version=1,
            supports_multiple_instances=cls.supports_multiple_instances,
            supports_actions=cls.supports_actions,
            supports_deep_link=cls.supports_deep_link,
            supports_dashboard_card=cls.supports_dashboard_card,
            supports_alerts=cls.supports_alerts,
        )

    def build_source_ref_selector(self):
        """Return the provider-specific selector for choosing the source."""
        return selector.TextSelector()

    def build_config_schema(self) -> vol.Schema:
        schema: dict[Any, Any] = {
            vol.Required(CONF_SOURCE_REF): self.build_source_ref_selector(),
        }
        if self.summary_limit_default is not None:
            schema[vol.Optional("summary_limit", default=self.summary_limit_default)] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=20, mode=selector.NumberSelectorMode.BOX)
            )
        return vol.Schema(schema)

    def validate_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        config = dict(user_input)
        config[CONF_SOURCE_TYPE] = self.source_type
        if self.summary_limit_default is not None:
            config["summary_limit"] = int(config.get("summary_limit", self.summary_limit_default))
        return config

    def build_reconfigure_schema(
        self,
        existing_data: dict[str, Any],
        existing_options: dict[str, Any],
    ) -> vol.Schema:
        return self.build_config_schema()

    async def async_collect(self, config: dict[str, Any]) -> dict[str, Any]:
        adapter = self.get_adapter()
        if adapter is not None:
            return await adapter.async_fetch(dict(config))

        return {
            "source_type": config.get("source_type"),
            "source_ref": config.get("source_ref"),
            "summary_limit": config.get("summary_limit", 3),
            "items": [],
        }

    def normalize(self, payload: dict[str, Any], instance_id: str) -> SnippetResult:
        title = self.describe().name
        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="empty",
            priority="optional",
            title=title,
            text=f"{title} provider scaffold is configured but not yet implemented.",
            scenario="empty",
            data=payload,
            meta={"scaffold": True},
        )

    def build_dashboard_fragments(self, entity_id_prefix: str) -> list[DashboardFragment]:
        return [
            DashboardFragment(
                fragment_key=f"{self.describe().key}_summary",
                provider_key=self.describe().key,
                title=self.describe().name,
                card_type="entities",
                entities=[entity_id_prefix],
            )
        ]

    def get_instance_title(self, config: dict[str, Any]) -> str:
        source_ref = config.get("source_ref")
        if source_ref:
            return f"{self.describe().name}: {source_ref}"
        return self.describe().name