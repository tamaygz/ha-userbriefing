"""Focused tests for dynamic snippet sensor lifecycle."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.user_briefing.const import DOMAIN, SUBENTRY_TYPE_SNIPPET
from custom_components.user_briefing.sensor import (
    UserBriefingSnippetSensor,
    async_setup_entry,
)
from custom_components.user_briefing.subentries import iter_config_subentries


class _FakeCoordinator:
    last_result = None

    def async_add_listener(self, listener):
        del listener
        return lambda: None

    def get_snippet_result(self, instance_id: str):
        del instance_id
        return None


class _FakeEntry:
    def __init__(self, subentries: dict[str, object]) -> None:
        self.entry_id = "entry-1"
        self.title = "Alex"
        self.subentries = subentries
        self._listeners = []
        self._unloaders = []

    def add_update_listener(self, listener):
        self._listeners.append(listener)

        def _remove_listener() -> None:
            self._listeners.remove(listener)

        return _remove_listener

    def async_on_unload(self, unsubscribe) -> None:
        self._unloaders.append(unsubscribe)

    async def async_fire_update(self) -> None:
        for listener in list(self._listeners):
            await listener(SimpleNamespace(), self)


class _AddEntitiesRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self.entities: list[object] = []
        self.updated_entities: list[object] = []

    def __call__(self, entities, **kwargs) -> None:
        entities = list(entities)
        self.calls.append(kwargs)
        self.entities.extend(entities)
        for entity in entities:
            entity.async_remove = AsyncMock()
            entity.async_write_ha_state = Mock(
                side_effect=lambda entity=entity: self.updated_entities.append(entity)
            )


def _subentry(subentry_id: str, title: str) -> SimpleNamespace:
    return SimpleNamespace(
        subentry_id=subentry_id,
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        title=title,
        data={},
        options={},
    )


def test_iter_config_subentries_supports_id_keyed_mappings() -> None:
    subentry = _subentry("snippet-1", "Calendar")
    entry = SimpleNamespace(subentries={"snippet-1": subentry})

    assert list(iter_config_subentries(entry, SUBENTRY_TYPE_SNIPPET)) == [subentry]


def test_async_setup_entry_syncs_snippet_sensor_lifecycle() -> None:
    entry = _FakeEntry({"snippet-1": _subentry("snippet-1", "Calendar")})
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: _FakeCoordinator()}})
    add_entities = _AddEntitiesRecorder()

    asyncio.run(async_setup_entry(hass, entry, add_entities))

    snippet_entities = [
        entity for entity in add_entities.entities if isinstance(entity, UserBriefingSnippetSensor)
    ]
    assert [entity.subentry_id for entity in snippet_entities] == ["snippet-1"]
    assert add_entities.calls[1] == {"config_subentry_id": "snippet-1"}

    entry.subentries["snippet-1"].title = "Updated Calendar"
    entry.subentries["snippet-2"] = _subentry("snippet-2", "Weather")

    asyncio.run(entry.async_fire_update())

    snippet_entities = {
        entity.subentry_id: entity
        for entity in add_entities.entities
        if isinstance(entity, UserBriefingSnippetSensor)
    }
    assert snippet_entities["snippet-1"].name == "Alex Updated Calendar"
    assert snippet_entities["snippet-1"] in add_entities.updated_entities
    assert snippet_entities["snippet-2"].name == "Alex Weather"
    assert add_entities.calls[2] == {"config_subentry_id": "snippet-2"}

    snippet_entities["snippet-2"].async_remove.reset_mock()
    entry.subentries.pop("snippet-2")

    asyncio.run(entry.async_fire_update())

    snippet_entities["snippet-2"].async_remove.assert_awaited_once()
