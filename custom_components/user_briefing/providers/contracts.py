"""Provider and adapter contracts for User Briefing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant

from ..models import DashboardFragment, ProviderMetadata, SnippetResult


class ProviderAdapter(ABC):
    """Base adapter for upstream data sources."""

    @abstractmethod
    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        """Fetch raw data from the source."""


class BriefingProvider(ABC):
    """Base provider contract."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @classmethod
    @abstractmethod
    def describe(cls) -> ProviderMetadata:
        """Describe provider metadata."""

    @abstractmethod
    def build_config_schema(self) -> vol.Schema:
        """Build setup schema for the provider-specific source config."""

    def build_reconfigure_schema(
        self,
        existing_data: dict[str, Any],
        existing_options: dict[str, Any],
    ) -> vol.Schema:
        """Build reconfigure schema for existing provider config."""
        return self.build_config_schema()

    def build_options_schema(self) -> vol.Schema | None:
        """Build optional mutable schema for provider-level settings."""
        return None

    @abstractmethod
    def validate_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate provider-specific configuration."""

    def validate_reconfigure_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate provider-specific reconfigure input."""
        return self.validate_config(user_input)

    @abstractmethod
    async def async_collect(self, config: dict[str, Any]) -> dict[str, Any]:
        """Collect raw provider payload."""

    @abstractmethod
    def normalize(self, payload: dict[str, Any], instance_id: str) -> SnippetResult:
        """Normalize provider payload to a snippet result."""

    def build_phrase_context(self, snippet: SnippetResult) -> dict[str, Any]:
        """Return a phrase interpolation context for the snippet."""
        return snippet.data

    def build_actions(self, snippet: SnippetResult) -> list[dict[str, Any]]:
        """Return future-facing action metadata."""
        return []

    def get_instance_title(self, config: dict[str, Any]) -> str:
        """Return a suggested instance title for the configured provider."""
        return self.describe().name

    def get_instance_unique_key(self, config: dict[str, Any]) -> str | None:
        """Return a provider-specific unique key for duplicate detection."""
        source_type = config.get("source_type")
        source_ref = config.get("source_ref")
        if source_type and source_ref:
            return f"{source_type}:{source_ref}"
        return None

    def build_dashboard_fragments(self, entity_id_prefix: str) -> list[DashboardFragment]:
        """Return dashboard fragments for this provider."""
        return []