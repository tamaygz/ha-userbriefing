"""Tests for User Briefing button entities."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.user_briefing.button import (
    UserBriefingDeliverButton,
    UserBriefingGenerateButton,
    async_setup_entry,
)
from custom_components.user_briefing.const import DOMAIN


class _FakeCoordinator:
    def __init__(self) -> None:
        self.last_result = None
        self._generate_called = False
        self._preview_called = False
        self.entry = SimpleNamespace(entry_id="entry-1", title="Alex")

    def async_add_listener(self, listener):
        del listener
        return lambda: None

    async def async_generate(self):
        self._generate_called = True

    async def async_preview(self):
        self._preview_called = True
        return SimpleNamespace(
            delivery_payloads={},
            snippets=[],
        )

    def get_snippet_result(self, instance_id: str):
        return None


class _FakeEntry:
    def __init__(self) -> None:
        self.entry_id = "entry-1"
        self.title = "Alex"


def test_async_setup_entry_adds_generate_and_deliver_buttons() -> None:
    """async_setup_entry should add exactly the generate and deliver buttons."""
    entry = _FakeEntry()
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: _FakeCoordinator()}})
    added: list[object] = []

    def add_entities(entities, **kwargs) -> None:
        added.extend(entities)

    asyncio.run(async_setup_entry(hass, entry, add_entities))

    assert len(added) == 2
    assert isinstance(added[0], UserBriefingGenerateButton)
    assert isinstance(added[1], UserBriefingDeliverButton)


def test_generate_button_metadata() -> None:
    """Generate button should have the expected name and unique_id."""
    entry = _FakeEntry()
    coordinator = _FakeCoordinator()
    button = UserBriefingGenerateButton(coordinator, entry)

    assert button.name == "Alex Generate Briefing"
    assert button.unique_id == "entry-1_generate"
    assert button.icon == "mdi:play-circle-outline"


def test_deliver_button_metadata() -> None:
    """Deliver button should have the expected name and unique_id."""
    entry = _FakeEntry()
    coordinator = _FakeCoordinator()
    button = UserBriefingDeliverButton(coordinator, entry)

    assert button.name == "Alex Deliver Briefing"
    assert button.unique_id == "entry-1_deliver"
    assert button.icon == "mdi:send-outline"


def test_generate_button_press_calls_coordinator() -> None:
    """Pressing generate button should call coordinator.async_generate()."""
    entry = _FakeEntry()
    coordinator = _FakeCoordinator()
    button = UserBriefingGenerateButton(coordinator, entry)

    asyncio.run(button.async_press())

    assert coordinator._generate_called is True


def test_deliver_button_press_uses_last_result_if_available() -> None:
    """Deliver button should use last_result when one is already cached."""
    entry = _FakeEntry()
    coordinator = _FakeCoordinator()
    coordinator.last_result = SimpleNamespace(
        delivery_payloads={"notification": {"title": "Good morning"}},
        snippets=[],
    )
    button = UserBriefingDeliverButton(coordinator, entry)

    asyncio.run(button.async_press())

    # Should not have called async_preview since last_result was available
    assert coordinator._preview_called is False


def test_deliver_button_press_previews_when_no_last_result() -> None:
    """Deliver button should call async_preview when no last_result exists."""
    entry = _FakeEntry()
    coordinator = _FakeCoordinator()
    button = UserBriefingDeliverButton(coordinator, entry)

    asyncio.run(button.async_press())

    assert coordinator._preview_called is True


def test_device_info_groups_entities_under_profile_device() -> None:
    """Both button entities should share device_info tied to the config entry."""
    entry = _FakeEntry()
    coordinator = _FakeCoordinator()
    generate_button = UserBriefingGenerateButton(coordinator, entry)
    deliver_button = UserBriefingDeliverButton(coordinator, entry)

    gen_info = generate_button.device_info
    del_info = deliver_button.device_info

    assert gen_info["identifiers"] == {(DOMAIN, "entry-1")}
    assert gen_info["name"] == "Alex"
    assert del_info["identifiers"] == gen_info["identifiers"]
    assert del_info["name"] == gen_info["name"]
