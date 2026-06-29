"""Basic tests for the provider registry."""

from custom_components.user_briefing.providers.registry import (
    ensure_builtin_providers_loaded,
    list_provider_metadata,
)


def test_builtin_provider_registry_loads() -> None:
    ensure_builtin_providers_loaded()
    provider_keys = {metadata.key for metadata in list_provider_metadata()}
    assert "calendar" in provider_keys
    assert "task_summary" in provider_keys
    assert "mail_summary_stub" in provider_keys