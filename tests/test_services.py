"""Tests for User Briefing service handlers.

Covers TEST-016 (preview non-mutation) and TEST-017 (required targets /
unknown config-entry rejection) from plan/design-user-briefing-1.md.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import voluptuous as vol
from homeassistant.exceptions import ServiceValidationError

from custom_components.user_briefing.const import (
    CONF_CONFIG_ENTRY_ID,
    CONF_SUBENTRY_ID,
    DOMAIN,
    SERVICE_DELIVER,
    SERVICE_GENERATE,
    SERVICE_PREVIEW,
    SERVICE_REFRESH_SNIPPET,
)
from custom_components.user_briefing.models import BriefingResult, SnippetResult
from custom_components.user_briefing.services import (
    _CONFIG_ENTRY_SCHEMA,
    _SNIPPET_SCHEMA,
    async_register_services,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeServices:
    """Minimal stand-in for hass.services that captures registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], object] = {}

    def has_service(self, domain: str, name: str) -> bool:
        return (domain, name) in self._handlers

    def async_register(self, domain: str, name: str, handler, **kwargs) -> None:
        self._handlers[(domain, name)] = handler

    def async_remove(self, domain: str, name: str) -> None:
        self._handlers.pop((domain, name), None)

    def get_handler(self, domain: str, name: str):
        return self._handlers[(domain, name)]


def _make_call(data: dict) -> SimpleNamespace:
    """Return a minimal ServiceCall-like object."""
    return SimpleNamespace(data=data)


def _make_result(
    user_key: str = "alex",
    summary_state: str = "empty",
    rendered_text: str = "",
    snippets: list | None = None,
) -> BriefingResult:
    return BriefingResult(
        user_key=user_key,
        generated_at=datetime.now(tz=timezone.utc),
        summary_state=summary_state,
        snippets=snippets or [],
        rendered_text=rendered_text,
    )


class _FakeCoordinator:
    """Minimal coordinator stand-in that records calls."""

    def __init__(self, preview_result: BriefingResult | None = None) -> None:
        self.last_result: BriefingResult | None = None
        self._generate_calls: list = []
        self._preview_result = preview_result or _make_result()

    def async_add_listener(self, listener):
        return lambda: None

    async def async_generate(self, subentry_ids=None) -> BriefingResult:
        self._generate_calls.append(subentry_ids)
        result = _make_result()
        self.last_result = result
        return result

    async def async_preview(self, subentry_ids=None) -> BriefingResult:
        return self._preview_result


def _make_hass(
    coordinator: _FakeCoordinator | None = None,
    entry_id: str = "entry-1",
) -> SimpleNamespace:
    """Build a minimal hass stand-in pre-populated with an optional coordinator."""
    services = _FakeServices()
    domain_data: dict = {entry_id: coordinator} if coordinator is not None else {}
    return SimpleNamespace(data={DOMAIN: domain_data}, services=services)


def _register(hass: SimpleNamespace) -> _FakeServices:
    """Register services and return the fake services registry."""
    asyncio.run(async_register_services(hass))
    return hass.services


# ---------------------------------------------------------------------------
# Required target semantics — schema-level validation (TEST-017)
# ---------------------------------------------------------------------------


def test_config_entry_schema_requires_config_entry_id() -> None:
    """_CONFIG_ENTRY_SCHEMA must reject a call with no config_entry_id field."""
    with pytest.raises(vol.Invalid):
        _CONFIG_ENTRY_SCHEMA({})


def test_config_entry_schema_accepts_valid_payload() -> None:
    """_CONFIG_ENTRY_SCHEMA must accept a call that provides config_entry_id."""
    result = _CONFIG_ENTRY_SCHEMA({CONF_CONFIG_ENTRY_ID: "entry-1"})
    assert result[CONF_CONFIG_ENTRY_ID] == "entry-1"


def test_snippet_schema_requires_both_ids() -> None:
    """_SNIPPET_SCHEMA must reject calls that omit either required field."""
    with pytest.raises(vol.Invalid):
        _SNIPPET_SCHEMA({CONF_CONFIG_ENTRY_ID: "entry-1"})
    with pytest.raises(vol.Invalid):
        _SNIPPET_SCHEMA({CONF_SUBENTRY_ID: "sub-1"})
    with pytest.raises(vol.Invalid):
        _SNIPPET_SCHEMA({})


def test_snippet_schema_accepts_valid_payload() -> None:
    """_SNIPPET_SCHEMA must accept a call that provides both required fields."""
    result = _SNIPPET_SCHEMA(
        {CONF_CONFIG_ENTRY_ID: "entry-1", CONF_SUBENTRY_ID: "sub-1"}
    )
    assert result[CONF_CONFIG_ENTRY_ID] == "entry-1"
    assert result[CONF_SUBENTRY_ID] == "sub-1"


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


def test_generate_calls_coordinator_async_generate() -> None:
    """generate service must delegate to coordinator.async_generate()."""
    coordinator = _FakeCoordinator()
    hass = _make_hass(coordinator)
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_GENERATE)
    asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "entry-1"})))

    assert len(coordinator._generate_calls) == 1
    # Profile-level generate passes no subentry filter.
    assert coordinator._generate_calls[0] is None


def test_generate_raises_for_unknown_config_entry_id() -> None:
    """generate must raise ServiceValidationError when no coordinator is found."""
    hass = _make_hass()  # empty domain data — no coordinator registered
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_GENERATE)
    with pytest.raises(ServiceValidationError):
        asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "no-such-entry"})))


# ---------------------------------------------------------------------------
# preview — response payload and non-mutation (TEST-016)
# ---------------------------------------------------------------------------


def test_preview_returns_expected_response_keys() -> None:
    """preview must return a dict containing the four documented response keys."""
    preview_result = _make_result(
        user_key="alex",
        summary_state="ready",
        rendered_text="Good morning, Alex!",
        snippets=[
            SnippetResult(
                provider_key="compliment",
                instance_id="s-1",
                status="ok",
                priority="optional",
                title="Compliment",
                text="You are doing great.",
                scenario="default",
            ),
            SnippetResult(
                provider_key="weather_forecast",
                instance_id="s-2",
                status="ok",
                priority="optional",
                title="Weather",
                text="Sunny.",
                scenario="default",
            ),
        ],
    )
    coordinator = _FakeCoordinator(preview_result=preview_result)
    hass = _make_hass(coordinator)
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_PREVIEW)
    response = asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "entry-1"})))

    assert response["user_key"] == "alex"
    assert response["summary_state"] == "ready"
    assert response["rendered_text"] == "Good morning, Alex!"
    assert response["snippet_count"] == 2


def test_preview_snippet_count_reflects_result_snippets() -> None:
    """snippet_count in the response must equal len(result.snippets)."""
    preview_result = _make_result(snippets=[])
    coordinator = _FakeCoordinator(preview_result=preview_result)
    hass = _make_hass(coordinator)
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_PREVIEW)
    response = asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "entry-1"})))

    assert response["snippet_count"] == 0


def test_preview_does_not_mutate_coordinator_last_result() -> None:
    """preview must NOT write to coordinator.last_result (TEST-016)."""
    coordinator = _FakeCoordinator()
    assert coordinator.last_result is None

    hass = _make_hass(coordinator)
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_PREVIEW)
    asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "entry-1"})))

    assert coordinator.last_result is None


def test_preview_raises_for_unknown_config_entry_id() -> None:
    """preview must raise ServiceValidationError when no coordinator is found."""
    hass = _make_hass()
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_PREVIEW)
    with pytest.raises(ServiceValidationError):
        asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "no-such-entry"})))


# ---------------------------------------------------------------------------
# refresh_snippet
# ---------------------------------------------------------------------------


def test_refresh_snippet_calls_coordinator_with_subentry_id() -> None:
    """refresh_snippet must call async_generate with the provided subentry_id."""
    coordinator = _FakeCoordinator()
    hass = _make_hass(coordinator)
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_REFRESH_SNIPPET)
    asyncio.run(
        handler(
            _make_call(
                {CONF_CONFIG_ENTRY_ID: "entry-1", CONF_SUBENTRY_ID: "sub-abc"}
            )
        )
    )

    assert coordinator._generate_calls == [{"sub-abc"}]


def test_refresh_snippet_raises_for_unknown_config_entry_id() -> None:
    """refresh_snippet must raise ServiceValidationError when no coordinator is found."""
    hass = _make_hass()
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_REFRESH_SNIPPET)
    with pytest.raises(ServiceValidationError):
        asyncio.run(
            handler(
                _make_call(
                    {
                        CONF_CONFIG_ENTRY_ID: "no-such-entry",
                        CONF_SUBENTRY_ID: "sub-abc",
                    }
                )
            )
        )


# ---------------------------------------------------------------------------
# deliver
# ---------------------------------------------------------------------------


def test_deliver_uses_cached_last_result_when_available() -> None:
    """deliver must not call async_preview when last_result is already cached."""
    coordinator = _FakeCoordinator()
    coordinator.last_result = _make_result()
    # Poison async_preview to detect if it is called.
    preview_called: list[bool] = []

    async def _poisoned_preview(**_kwargs):
        preview_called.append(True)
        return _make_result()

    coordinator.async_preview = _poisoned_preview  # type: ignore[method-assign]

    hass = _make_hass(coordinator)
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_DELIVER)
    asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "entry-1"})))

    assert preview_called == []


def test_deliver_calls_async_preview_when_no_last_result() -> None:
    """deliver must fall back to async_preview when no result is cached."""
    preview_called: list[bool] = []

    class _TrackingCoordinator(_FakeCoordinator):
        async def async_preview(self, subentry_ids=None):
            preview_called.append(True)
            return _make_result()

    coordinator = _TrackingCoordinator()
    assert coordinator.last_result is None

    hass = _make_hass(coordinator)
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_DELIVER)
    asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "entry-1"})))

    assert preview_called == [True]


def test_deliver_raises_for_unknown_config_entry_id() -> None:
    """deliver must raise ServiceValidationError when no coordinator is found."""
    hass = _make_hass()
    services = _register(hass)

    handler = services.get_handler(DOMAIN, SERVICE_DELIVER)
    with pytest.raises(ServiceValidationError):
        asyncio.run(handler(_make_call({CONF_CONFIG_ENTRY_ID: "no-such-entry"})))
