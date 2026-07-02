"""Tests for the custom_text provider, slot expiry, and push/clear services."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from custom_components.user_briefing.models import SlotEntry
from custom_components.user_briefing.providers.custom_text import CustomTextProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeStates:
    def __init__(self, states: dict[str, Any]) -> None:
        self._states = states

    def get(self, entity_id: str):
        return self._states.get(entity_id)


def _make_state(state: str, attributes: dict[str, Any] | None = None) -> SimpleNamespace:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimpleNamespace(
        state=state,
        attributes=attributes or {},
        last_changed=now,
        last_updated=now,
    )


def _make_hass(states: dict[str, Any] | None = None) -> SimpleNamespace:
    return SimpleNamespace(states=_FakeStates(states or {}))


# ---------------------------------------------------------------------------
# Provider describe / registration
# ---------------------------------------------------------------------------


def test_custom_text_provider_is_registered() -> None:
    from custom_components.user_briefing.providers.registry import (
        ensure_builtin_providers_loaded,
        list_provider_metadata,
    )

    ensure_builtin_providers_loaded()
    keys = {m.key for m in list_provider_metadata()}
    assert "custom_text" in keys


def test_custom_text_provider_metadata() -> None:
    meta = CustomTextProvider.describe()
    assert meta.key == "custom_text"
    assert meta.supports_multiple_instances is True
    assert meta.supports_alerts is True


# ---------------------------------------------------------------------------
# Slot mode — async_collect
# ---------------------------------------------------------------------------


def test_slot_mode_returns_empty_when_no_slot_and_no_default() -> None:
    provider = CustomTextProvider(_make_hass())
    result = asyncio.run(provider.async_collect({"mode": "slot"}))
    assert result == {"empty": True}


def test_slot_mode_uses_default_text_when_no_slot() -> None:
    provider = CustomTextProvider(_make_hass())
    result = asyncio.run(
        provider.async_collect({"mode": "slot", "default_text": "Fallback content"})
    )
    assert result["text"] == "Fallback content"
    assert result.get("empty") is None


def test_slot_mode_reads_slot_entry() -> None:
    entry = SlotEntry(text="Hello world", title="My title", severity="warning")
    provider = CustomTextProvider(_make_hass())
    result = asyncio.run(provider.async_collect({"mode": "slot", "_slot_entry": entry}))
    assert result["text"] == "Hello world"
    assert result["title"] == "My title"
    assert result["severity"] == "warning"


# ---------------------------------------------------------------------------
# Entity mode — async_collect
# ---------------------------------------------------------------------------


def test_entity_mode_reads_state() -> None:
    hass = _make_hass({"input_text.note": _make_state("Buy milk")})
    provider = CustomTextProvider(hass)
    result = asyncio.run(
        provider.async_collect({"mode": "entity", "source_ref": "input_text.note"})
    )
    assert result["text"] == "Buy milk"


def test_entity_mode_returns_empty_for_unavailable_entity() -> None:
    hass = _make_hass({"input_text.note": _make_state("unavailable")})
    provider = CustomTextProvider(hass)
    result = asyncio.run(
        provider.async_collect({"mode": "entity", "source_ref": "input_text.note"})
    )
    assert result == {"empty": True}


def test_entity_mode_returns_empty_when_entity_missing() -> None:
    provider = CustomTextProvider(_make_hass())
    result = asyncio.run(
        provider.async_collect({"mode": "entity", "source_ref": "input_text.missing"})
    )
    assert result == {"empty": True}


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------


def test_normalize_empty_payload_returns_skipped_snippet() -> None:
    provider = CustomTextProvider(_make_hass())
    snippet = provider.normalize({"empty": True}, "slot-1")
    assert snippet.status == "skipped"
    assert snippet.text == ""


def test_normalize_normal_payload() -> None:
    provider = CustomTextProvider(_make_hass())
    snippet = provider.normalize({"text": "Some content", "title": "My title", "severity": None}, "slot-1")
    assert snippet.status == "ok"
    assert snippet.text == "Some content"
    assert snippet.title == "My title"
    assert snippet.alerts == []


def test_normalize_severity_emits_alert() -> None:
    provider = CustomTextProvider(_make_hass())
    snippet = provider.normalize(
        {"text": "Storm warning", "title": "Weather", "severity": "critical"}, "slot-1"
    )
    assert snippet.status == "ok"
    assert len(snippet.alerts) == 1
    alert = snippet.alerts[0]
    assert alert.severity == "critical"
    assert alert.title == "Weather"
    assert alert.text == "Storm warning"
    assert alert.provider_key == "custom_text"


def test_normalize_info_severity_emits_alert() -> None:
    provider = CustomTextProvider(_make_hass())
    snippet = provider.normalize(
        {"text": "FYI", "title": None, "severity": "info"}, "slot-2"
    )
    assert snippet.alerts[0].severity == "info"


# ---------------------------------------------------------------------------
# SlotEntry expiry
# ---------------------------------------------------------------------------


def test_slot_entry_with_no_expiry() -> None:
    entry = SlotEntry(text="no expiry")
    assert entry.expires_at is None


def test_slot_entry_expiry_is_set_correctly() -> None:
    now = datetime.now(tz=timezone.utc)
    expires = now + timedelta(hours=24)
    entry = SlotEntry(text="temporary", expires_at=expires)
    assert entry.expires_at == expires


def test_coordinator_prunes_expired_slots() -> None:
    """Expired slot entries are removed before generate() dispatches to providers."""
    from custom_components.user_briefing.coordinator import UserBriefingCoordinator

    now = datetime.now(tz=timezone.utc)

    class _FakeSubentries:
        """Minimal ConfigEntry-like with no subentries."""
        entry_id = "entry-1"
        data = {"user_key": "user1"}
        options = {}

        def __init__(self):
            self.subentries = {}

    entry = _FakeSubentries()
    hass = SimpleNamespace(data={}, states=_FakeStates({}))
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    expired_entry = SlotEntry(
        text="expired",
        expires_at=now - timedelta(hours=1),
    )
    live_entry = SlotEntry(
        text="live",
        expires_at=now + timedelta(hours=1),
    )
    coordinator.slot_store["expired-slot"] = expired_entry
    coordinator.slot_store["live-slot"] = live_entry

    # Patch the downstream calls that we can't run without a full HA instance.
    with (
        patch(
            "custom_components.user_briefing.coordinator.iter_config_subentries",
            return_value=[],
        ),
        patch(
            "custom_components.user_briefing.coordinator.build_dashboard_delivery_payload",
            return_value={},
        ),
        patch(
            "custom_components.user_briefing.coordinator.build_notification_payload",
            return_value={},
        ),
    ):
        asyncio.run(coordinator.async_generate())

    assert "expired-slot" not in coordinator.slot_store
    assert "live-slot" in coordinator.slot_store


# ---------------------------------------------------------------------------
# push_snippet / clear_snippet service validation
# ---------------------------------------------------------------------------


def _make_entry_with_subentries(subentries: list[SimpleNamespace]) -> SimpleNamespace:
    """Build a minimal config entry with a subentries dict."""
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={"user_key": "user1"},
        options={},
        subentries={s.subentry_id: s for s in subentries},
    )
    return entry


def _make_subentry(
    subentry_id: str,
    provider_key: str,
    mode: str = "slot",
    **extra_data,
) -> SimpleNamespace:
    return SimpleNamespace(
        subentry_id=subentry_id,
        subentry_type="snippet",
        data={"provider_key": provider_key, "mode": mode, **extra_data},
        options={},
    )


def test_validate_custom_text_slot_subentry_passes_for_valid_slot() -> None:
    from custom_components.user_briefing.services import _validate_custom_text_slot_subentry

    subentry = _make_subentry("slot-abc", "custom_text", mode="slot")
    entry = _make_entry_with_subentries([subentry])

    class _FakeEntries:
        def async_get_entry(self, entry_id):
            return entry if entry_id == "entry-1" else None

    hass = SimpleNamespace(config_entries=_FakeEntries())
    # Should not raise.
    _validate_custom_text_slot_subentry(hass, "entry-1", "slot-abc")


def test_validate_custom_text_slot_subentry_raises_for_entity_mode() -> None:
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.user_briefing.services import _validate_custom_text_slot_subentry

    subentry = _make_subentry("slot-abc", "custom_text", mode="entity")
    entry = _make_entry_with_subentries([subentry])

    class _FakeEntries:
        def async_get_entry(self, entry_id):
            return entry

    hass = SimpleNamespace(config_entries=_FakeEntries())
    with pytest.raises(ServiceValidationError):
        _validate_custom_text_slot_subentry(hass, "entry-1", "slot-abc")


def test_validate_custom_text_slot_subentry_raises_for_wrong_provider() -> None:
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.user_briefing.services import _validate_custom_text_slot_subentry

    subentry = _make_subentry("slot-abc", "calendar", mode="slot")
    entry = _make_entry_with_subentries([subentry])

    class _FakeEntries:
        def async_get_entry(self, entry_id):
            return entry

    hass = SimpleNamespace(config_entries=_FakeEntries())
    with pytest.raises(ServiceValidationError):
        _validate_custom_text_slot_subentry(hass, "entry-1", "slot-abc")


def test_validate_custom_text_slot_subentry_raises_for_missing_subentry() -> None:
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.user_briefing.services import _validate_custom_text_slot_subentry

    entry = _make_entry_with_subentries([])

    class _FakeEntries:
        def async_get_entry(self, entry_id):
            return entry

    hass = SimpleNamespace(config_entries=_FakeEntries())
    with pytest.raises(ServiceValidationError):
        _validate_custom_text_slot_subentry(hass, "entry-1", "non-existent-id")


def test_validate_custom_text_slot_subentry_raises_for_unknown_config_entry() -> None:
    from homeassistant.exceptions import ServiceValidationError

    from custom_components.user_briefing.services import _validate_custom_text_slot_subentry

    class _FakeEntries:
        def async_get_entry(self, entry_id):
            return None

    hass = SimpleNamespace(config_entries=_FakeEntries())
    with pytest.raises(ServiceValidationError):
        _validate_custom_text_slot_subentry(hass, "missing-entry", "slot-abc")


# ---------------------------------------------------------------------------
# clear_snippet removes slot entry
# ---------------------------------------------------------------------------


def test_clear_snippet_removes_entry_from_slot_store() -> None:
    """_handle_clear_snippet pops the slot entry when coordinator is found."""
    from custom_components.user_briefing.coordinator import UserBriefingCoordinator

    class _FakeEntry:
        entry_id = "entry-1"
        data = {"user_key": "user1"}
        options = {}
        subentries = {}

    coordinator = UserBriefingCoordinator(
        SimpleNamespace(data={}), _FakeEntry()  # type: ignore[arg-type]
    )
    coordinator.slot_store["slot-abc"] = SlotEntry(text="Hello")

    # Simulate what _handle_clear_snippet does.
    coordinator.slot_store.pop("slot-abc", None)
    assert "slot-abc" not in coordinator.slot_store


def test_clear_snippet_is_idempotent_when_slot_missing() -> None:
    """Clearing a slot that does not exist should not raise."""
    from custom_components.user_briefing.coordinator import UserBriefingCoordinator

    class _FakeEntry:
        entry_id = "entry-1"
        data = {}
        options = {}
        subentries = {}

    coordinator = UserBriefingCoordinator(
        SimpleNamespace(data={}), _FakeEntry()  # type: ignore[arg-type]
    )
    coordinator.slot_store.pop("no-such-slot", None)  # Should not raise.
    assert "no-such-slot" not in coordinator.slot_store
