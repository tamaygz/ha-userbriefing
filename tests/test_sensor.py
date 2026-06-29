"""Focused tests for dynamic snippet sensor lifecycle."""

import asyncio
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.user_briefing.const import DOMAIN, SUBENTRY_TYPE_SNIPPET
from custom_components.user_briefing.sensor import (
    UserBriefingSnippetEntityManager,
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
    def __init__(self, subentries: dict[str, SimpleNamespace]) -> None:
        self.entry_id = "entry-1"
        self.title = "Alex"
        self.subentries: dict[str, SimpleNamespace] = subentries
        self._listeners: list[Callable[[SimpleNamespace, object], Awaitable[None]]] = []
        self._unloaders: list[Callable[[], None]] = []

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

    snippet_entities_by_id = {
        entity.subentry_id: entity
        for entity in add_entities.entities
        if isinstance(entity, UserBriefingSnippetSensor)
    }
    assert snippet_entities_by_id["snippet-1"].name == "Alex Updated Calendar"
    assert snippet_entities_by_id["snippet-1"] in add_entities.updated_entities
    assert snippet_entities_by_id["snippet-2"].name == "Alex Weather"
    assert add_entities.calls[2] == {"config_subentry_id": "snippet-2"}

    snippet_entities_by_id["snippet-2"].async_remove.reset_mock()
    entry.subentries.pop("snippet-2")

    asyncio.run(entry.async_fire_update())

    snippet_entities_by_id["snippet-2"].async_remove.assert_awaited_once()


def test_async_setup_entry_falls_back_without_config_subentry_id_support() -> None:
    entry = _FakeEntry({"snippet-1": _subentry("snippet-1", "Calendar")})
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: _FakeCoordinator()}})
    # Recorder patches entities with mocks AND raises TypeError for config_subentry_id.
    # Raising on the first attempt triggers the compatibility fallback; the second
    # plain-call then patches the entity so async_write_ha_state() is safe later.
    recorder = _AddEntitiesRecorder()
    original_call = recorder.__class__.__call__

    def limited_call(self_rec, entities, **kwargs) -> None:
        if "config_subentry_id" in kwargs:
            raise TypeError("got an unexpected keyword argument 'config_subentry_id'")
        original_call(self_rec, entities, **kwargs)

    recorder.__class__ = type(
        "_LimitedRecorder",
        (_AddEntitiesRecorder,),
        {"__call__": limited_call},
    )

    asyncio.run(async_setup_entry(hass, entry, recorder))

    snippet_calls = [
        c for c in recorder.calls
        if any(isinstance(e, UserBriefingSnippetSensor) for e in recorder.entities)
    ]
    # At least one plain-call (no kwargs) added the snippet entity after the fallback
    assert len(snippet_calls) >= 1
    assert all(c == {} for c in snippet_calls)

    # Flag stays latched — second subentry also added without the kwarg
    entry.subentries["snippet-2"] = _subentry("snippet-2", "Weather")
    asyncio.run(entry.async_fire_update())

    new_snippet_entities = [
        e for e in recorder.entities
        if isinstance(e, UserBriefingSnippetSensor)
        and getattr(e, "subentry_id", None) == "snippet-2"
    ]
    assert len(new_snippet_entities) == 1
    # All calls after setup should have empty kwargs (flag stayed False)
    assert all(c == {} for c in recorder.calls[2:])  # calls[0:2] are profile sensors


def test_async_add_snippet_entities_reraises_unrelated_type_error() -> None:
    """TypeError unrelated to config_subentry_id must propagate, not be swallowed."""
    import pytest

    coordinator = _FakeCoordinator()
    entry = _FakeEntry({"snippet-1": _subentry("snippet-1", "Calendar")})

    def broken_add_entities(entities, **kwargs) -> None:
        # Raises a TypeError whose message does NOT contain "unexpected keyword argument"
        raise TypeError("bad value type for entities argument")

    manager = UserBriefingSnippetEntityManager(coordinator, entry, broken_add_entities)
    entity = UserBriefingSnippetSensor(coordinator, entry, _subentry("s1", "Cal"))

    with pytest.raises(TypeError, match="bad value type"):
        manager._async_add_snippet_entities([entity])
