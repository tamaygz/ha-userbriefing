"""Shared stub implementation helpers for built-in providers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.helpers import selector

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
        )

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("source_type", default="entity"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["entity", "service", "integration"],
                        translation_key="provider_source_type",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("source_ref"): selector.TextSelector(),
                vol.Optional("summary_limit", default=3): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=20, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )

    def validate_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return dict(user_input)

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