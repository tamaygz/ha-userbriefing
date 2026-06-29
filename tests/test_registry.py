"""Basic tests for the provider registry and integration adapters."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from custom_components.user_briefing.adapters.base import (
    HomeAssistantEntityAdapter,
    HomeAssistantServiceAdapter,
    StubAdapter,
)
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


class _FakeStates:
    def __init__(self, states: dict[str, Any]) -> None:
        self._states = states

    def get(self, entity_id: str):
        return self._states.get(entity_id)


class _FakeServices:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def async_call(self, domain, service, data, blocking=False, return_response=False):
        self.calls.append((domain, service, data))
        return self._response


def _make_state(state: str, attributes: dict[str, Any] | None = None) -> SimpleNamespace:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimpleNamespace(
        state=state,
        attributes=attributes or {},
        last_changed=now,
        last_updated=now,
    )


def test_entity_adapter_reads_state_and_attributes() -> None:
    hass = SimpleNamespace(
        states=_FakeStates(
            {"sensor.demo": _make_state("21.5", {"friendly_name": "Demo", "unit": "C"})}
        )
    )
    adapter = HomeAssistantEntityAdapter(hass)

    result = asyncio.run(adapter.async_fetch({"source_ref": "sensor.demo"}))

    assert result["available"] is True
    assert result["state"] == "21.5"
    assert result["attributes"]["unit"] == "C"


def test_entity_adapter_handles_missing_entity() -> None:
    hass = SimpleNamespace(states=_FakeStates({}))
    adapter = HomeAssistantEntityAdapter(hass)

    result = asyncio.run(adapter.async_fetch({"source_ref": "sensor.missing"}))

    assert result["available"] is False
    assert result["items"] == []


def test_service_adapter_calls_service_with_response() -> None:
    services = _FakeServices({"events": [{"summary": "Standup"}]})
    hass = SimpleNamespace(services=services)
    adapter = HomeAssistantServiceAdapter(hass)

    result = asyncio.run(
        adapter.async_fetch(
            {
                "service_domain": "calendar",
                "service_name": "get_events",
                "target": {"entity_id": "calendar.work"},
            }
        )
    )

    assert result["available"] is True
    assert result["response"]["events"][0]["summary"] == "Standup"
    assert services.calls[0][0] == "calendar"


def test_service_adapter_requires_domain_and_name() -> None:
    hass = SimpleNamespace(services=_FakeServices(None))
    adapter = HomeAssistantServiceAdapter(hass)

    result = asyncio.run(adapter.async_fetch({}))

    assert result["available"] is False


def test_stub_adapter_returns_empty_items() -> None:
    adapter = StubAdapter(SimpleNamespace())
    result = asyncio.run(adapter.async_fetch({"source_ref": "sensor.demo"}))
    assert result["items"] == []