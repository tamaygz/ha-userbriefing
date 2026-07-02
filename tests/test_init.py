"""Integration entry-point lifecycle tests.

Covers async_setup, async_setup_entry, and async_unload_entry behavior from
custom_components/user_briefing/__init__.py without requiring a full Home
Assistant instance.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hass(existing_services: set | None = None) -> SimpleNamespace:
    """Return a minimal mock HomeAssistant suitable for __init__ lifecycle tests."""
    registered: dict[tuple[str, str], object] = {}
    _existing = existing_services or set()

    class _Services:
        def has_service(self, domain: str, name: str) -> bool:
            return (domain, name) in registered or (domain, name) in _existing

        def async_register(self, domain, name, handler, **kwargs):
            registered[(domain, name)] = handler

        def async_remove(self, domain, name):
            registered.pop((domain, name), None)

    class _ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            pass

        async def async_unload_platforms(self, entry, platforms):
            return True

    hass = SimpleNamespace(
        data={},
        services=_Services(),
        config_entries=_ConfigEntries(),
        _registered=registered,
    )
    return hass


def _make_entry(entry_id: str = "test-entry-1") -> SimpleNamespace:
    return SimpleNamespace(
        entry_id=entry_id,
        data={"user_key": "user1"},
        options={},
        subentries={},
    )


# ---------------------------------------------------------------------------
# async_setup
# ---------------------------------------------------------------------------


def test_async_setup_initialises_domain_data_and_returns_true() -> None:
    """async_setup must initialise hass.data[DOMAIN] and return True."""
    from custom_components.user_briefing import async_setup
    from custom_components.user_briefing.const import DOMAIN

    hass = _make_hass()
    result = asyncio.run(async_setup(hass, {}))

    assert result is True
    assert DOMAIN in hass.data


def test_async_setup_registers_services() -> None:
    """async_setup must register all public services."""
    from custom_components.user_briefing import async_setup
    from custom_components.user_briefing.const import (
        DOMAIN,
        SERVICE_GENERATE,
        SERVICE_PREVIEW,
        SERVICE_DELIVER,
        SERVICE_REFRESH_SNIPPET,
        SERVICE_PUSH_SNIPPET,
        SERVICE_CLEAR_SNIPPET,
    )

    hass = _make_hass()
    asyncio.run(async_setup(hass, {}))

    for svc in (
        SERVICE_GENERATE,
        SERVICE_PREVIEW,
        SERVICE_DELIVER,
        SERVICE_REFRESH_SNIPPET,
        SERVICE_PUSH_SNIPPET,
        SERVICE_CLEAR_SNIPPET,
    ):
        assert hass.services.has_service(DOMAIN, svc), (
            f"Service {DOMAIN}.{svc} must be registered after async_setup"
        )


def test_async_setup_idempotent_when_called_twice() -> None:
    """Calling async_setup a second time must not raise or double-register services."""
    from custom_components.user_briefing import async_setup

    hass = _make_hass()
    asyncio.run(async_setup(hass, {}))
    # Second call must be a no-op and still return True.
    result = asyncio.run(async_setup(hass, {}))
    assert result is True


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------


def test_async_setup_entry_creates_coordinator_in_domain_data() -> None:
    """async_setup_entry must store a coordinator in hass.data[DOMAIN][entry_id]."""
    from custom_components.user_briefing import async_setup_entry
    from custom_components.user_briefing.const import DOMAIN
    from custom_components.user_briefing.coordinator import UserBriefingCoordinator

    hass = _make_hass()
    hass.data[DOMAIN] = {}
    entry = _make_entry("entry-abc")

    asyncio.run(async_setup_entry(hass, entry))

    assert "entry-abc" in hass.data[DOMAIN]
    assert isinstance(hass.data[DOMAIN]["entry-abc"], UserBriefingCoordinator)


def test_async_setup_entry_returns_true() -> None:
    """async_setup_entry must return True on success."""
    from custom_components.user_briefing import async_setup_entry
    from custom_components.user_briefing.const import DOMAIN

    hass = _make_hass()
    hass.data[DOMAIN] = {}
    entry = _make_entry("entry-xyz")

    result = asyncio.run(async_setup_entry(hass, entry))

    assert result is True


# ---------------------------------------------------------------------------
# async_unload_entry
# ---------------------------------------------------------------------------


def test_async_unload_entry_removes_coordinator_from_domain_data() -> None:
    """async_unload_entry must pop the coordinator from hass.data[DOMAIN]."""
    from custom_components.user_briefing import async_setup_entry, async_unload_entry
    from custom_components.user_briefing.const import DOMAIN

    hass = _make_hass()
    hass.data[DOMAIN] = {}
    entry = _make_entry("entry-1")

    asyncio.run(async_setup_entry(hass, entry))
    assert "entry-1" in hass.data[DOMAIN]

    asyncio.run(async_unload_entry(hass, entry))
    assert "entry-1" not in hass.data[DOMAIN]


def test_async_unload_entry_unregisters_services_when_last_entry_removed() -> None:
    """async_unload_entry must unregister services once no config entries remain."""
    from custom_components.user_briefing import async_setup, async_setup_entry, async_unload_entry
    from custom_components.user_briefing.const import DOMAIN, SERVICE_GENERATE

    hass = _make_hass()
    asyncio.run(async_setup(hass, {}))
    entry = _make_entry("only-entry")
    asyncio.run(async_setup_entry(hass, entry))

    assert hass.services.has_service(DOMAIN, SERVICE_GENERATE)

    asyncio.run(async_unload_entry(hass, entry))

    assert not hass.services.has_service(DOMAIN, SERVICE_GENERATE), (
        "Services must be unregistered when the last config entry is removed"
    )


def test_async_unload_entry_returns_true() -> None:
    """async_unload_entry must return True when unload succeeds."""
    from custom_components.user_briefing import async_setup_entry, async_unload_entry
    from custom_components.user_briefing.const import DOMAIN

    hass = _make_hass()
    hass.data[DOMAIN] = {}
    entry = _make_entry("entry-ret")

    asyncio.run(async_setup_entry(hass, entry))
    result = asyncio.run(async_unload_entry(hass, entry))
    assert result is True
