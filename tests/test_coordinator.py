"""Coordinator integration tests."""

from __future__ import annotations

import asyncio
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

from custom_components.user_briefing.coordinator import UserBriefingCoordinator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_compliment_subentry(subentry_id: str = "s1") -> SimpleNamespace:
    return SimpleNamespace(
        subentry_id=subentry_id,
        subentry_type="snippet",
        title="Compliment",
        data={"provider_key": "compliment"},
        options={"enabled": True, "order": 100, "priority": "optional", "title_override": None},
    )


def _make_hass() -> SimpleNamespace:
    return SimpleNamespace(data={})


def _run(coro):
    return asyncio.run(coro)


_DELIVERY_PATCHES = (
    patch(
        "custom_components.user_briefing.coordinator.build_dashboard_delivery_payload",
        return_value={},
    ),
    patch(
        "custom_components.user_briefing.coordinator.build_notification_payload",
        return_value={},
    ),
)


# ---------------------------------------------------------------------------
# Regression test: MappingProxyType subentries (GitHub issue #43)
# ---------------------------------------------------------------------------


def test_generate_with_mapping_proxy_type_subentries_produces_ready_briefing() -> None:
    """Regression: HA stores config_entry.subentries as MappingProxyType, not dict.

    Before the fix, ``iter_config_subentries`` used ``isinstance(x, dict)`` which
    returns ``False`` for ``MappingProxyType``.  The function then fell through to
    iterate over the mapping *keys* (string subentry IDs) instead of the subentry
    objects, yielding nothing and leaving the briefing always empty.
    """
    sub = _make_compliment_subentry()
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries=MappingProxyType({"s1": sub}),
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "ready", (
        "Briefing should be 'ready' with a compliment subentry; got 'empty'. "
        "Check that iter_config_subentries handles MappingProxyType correctly."
    )
    assert len(result.snippets) == 1
    assert result.snippets[0].provider_key == "compliment"
    assert result.rendered_text  # non-empty


def test_generate_with_plain_dict_subentries_produces_ready_briefing() -> None:
    """Plain-dict subentries (test / older-HA path) still work after the fix."""
    sub = _make_compliment_subentry()
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries={"s1": sub},
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "ready"
    assert len(result.snippets) == 1
    assert result.rendered_text


def test_generate_with_no_subentries_produces_empty_briefing() -> None:
    """Empty subentries dict → summary_state='empty'."""
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries={},
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "empty"
    assert result.snippets == []


def test_generate_with_disabled_subentry_produces_empty_briefing() -> None:
    """A disabled snippet subentry is skipped, leaving the briefing empty."""
    sub = SimpleNamespace(
        subentry_id="s1",
        subentry_type="snippet",
        title="Compliment",
        data={"provider_key": "compliment"},
        options={"enabled": False, "order": 100, "priority": "optional", "title_override": None},
    )
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries=MappingProxyType({"s1": sub}),
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "empty"


def test_generate_with_unknown_provider_key_logs_and_continues() -> None:
    """An unregistered provider key is caught inside the try block and skipped."""
    sub = SimpleNamespace(
        subentry_id="s1",
        subentry_type="snippet",
        title="Unknown",
        data={"provider_key": "nonexistent_provider_xyz"},
        options={"enabled": True, "order": 100, "priority": "optional", "title_override": None},
    )
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries=MappingProxyType({"s1": sub}),
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        # Must not raise; unknown provider should be caught and logged.
        result = _run(coordinator.async_generate())

    assert result.summary_state == "empty"
    assert coordinator.last_result is not None
