"""Provider and adapter contracts for User Briefing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant

from ..models import DashboardFragment, ProviderMetadata, SnippetResult


class ProviderAdapter(ABC):
    """Base adapter for upstream data sources.

    Adapters are the seam that lets providers consume existing Home Assistant
    integrations (core or HACS) without the provider, composer, or rendering
    layers knowing transport details. Most adapters should read from existing
    integration entities or services rather than talking to external APIs
    directly.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    @abstractmethod
    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        """Fetch raw data from the source."""

    async def async_describe_source(self, source_ref: str) -> dict[str, Any]:
        """Return lightweight metadata about a configured source.

        Used for validation and UX hints. Override when an adapter can cheaply
        confirm a source exists or surface a friendly name.
        """
        return {"source_ref": source_ref}


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

    def prepare_collect_config(
        self,
        config: dict[str, Any],
        runtime_ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Enrich the collection config with runtime context before async_collect.

        The coordinator calls this once per snippet, passing a generic runtime
        context dict so providers can inject runtime data without the core
        orchestration knowing anything about provider-specific implementation
        details.  The default implementation returns ``config`` unchanged.

        ``runtime_ctx`` contains at minimum:
        - ``"subentry_id"`` (str): the subentry being processed
        - ``"slot_store"`` (dict): the coordinator's current in-memory slot store

        Providers that need to inject runtime data (e.g. ``custom_text`` for
        slot-mode entries) should override this method instead of expecting the
        coordinator to contain provider-specific branching logic.
        """
        return config

    @abstractmethod
    async def async_collect(self, config: dict[str, Any]) -> dict[str, Any]:
        """Collect raw provider payload."""

    def get_adapter(self) -> ProviderAdapter | None:
        """Return the source adapter this provider reads from, if any.

        Returning an adapter is the recommended way to consume existing Home
        Assistant integrations: the default ``async_collect`` will delegate to
        the adapter so a provider only has to normalize the result. Providers
        that derive data without an upstream source can return ``None``.
        """
        return None

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