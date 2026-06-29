"""Focused tests for dynamic snippet sensor lifecycle."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from custom_components.user_briefing.const import (
    ATTR_GENERATED_AT,
    DOMAIN,
    SUBENTRY_TYPE_SNIPPET,
)
from custom_components.user_briefing.sensor import (
    UserBriefingGeneratedAtSensor,
    UserBriefingSnippetEntityManager,
    UserBriefingSnippetSensor,
    UserBriefingSnippetStatusSensor,
    async_setup_entry,
)
from custom_components.user_briefing.subentries import iter_config_subentries


class _FakeCoordinator:
    def __init__(self) -> None:
        self.last_result = None
        self._snippet_results: dict[str, object] = {}

    def async_add_listener(self, listener):
        del listener
        return lambda: None

    def get_snippet_result(self, instance_id: str):
        return self._snippet_results.get(instance_id)


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
    snippet_status_entities = [
        entity
        for entity in add_entities.entities
        if isinstance(entity, UserBriefingSnippetStatusSensor)
    ]
    assert [entity.subentry_id for entity in snippet_entities] == ["snippet-1"]
    assert [entity.subentry_id for entity in snippet_status_entities] == ["snippet-1"]
    assert add_entities.calls[1:3] == [
        {"config_subentry_id": "snippet-1"},
        {"config_subentry_id": "snippet-1"},
    ]

    entry.subentries["snippet-1"].title = "Updated Calendar"
    entry.subentries["snippet-2"] = _subentry("snippet-2", "Weather")

    asyncio.run(entry.async_fire_update())

    snippet_entities_by_type = {
        (type(entity), entity.subentry_id): entity
        for entity in add_entities.entities
        if isinstance(entity, (UserBriefingSnippetSensor, UserBriefingSnippetStatusSensor))
    }
    assert (
        snippet_entities_by_type[(UserBriefingSnippetSensor, "snippet-1")].name
        == "Alex Updated Calendar"
    )
    assert (
        snippet_entities_by_type[(UserBriefingSnippetSensor, "snippet-1")]
        in add_entities.updated_entities
    )
    assert (
        snippet_entities_by_type[(UserBriefingSnippetStatusSensor, "snippet-1")].name
        == "Alex Updated Calendar Status"
    )
    assert (
        snippet_entities_by_type[(UserBriefingSnippetStatusSensor, "snippet-1")]
        in add_entities.updated_entities
    )
    assert (
        snippet_entities_by_type[(UserBriefingSnippetSensor, "snippet-2")].name
        == "Alex Weather"
    )
    assert (
        snippet_entities_by_type[(UserBriefingSnippetStatusSensor, "snippet-2")].name
        == "Alex Weather Status"
    )
    assert add_entities.calls[3:5] == [
        {"config_subentry_id": "snippet-2"},
        {"config_subentry_id": "snippet-2"},
    ]

    snippet_entities_by_type[(UserBriefingSnippetSensor, "snippet-2")].async_remove.reset_mock()
    snippet_entities_by_type[
        (UserBriefingSnippetStatusSensor, "snippet-2")
    ].async_remove.reset_mock()
    entry.subentries.pop("snippet-2")

    asyncio.run(entry.async_fire_update())

    snippet_entities_by_type[
        (UserBriefingSnippetSensor, "snippet-2")
    ].async_remove.assert_awaited_once()
    snippet_entities_by_type[
        (UserBriefingSnippetStatusSensor, "snippet-2")
    ].async_remove.assert_awaited_once()


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
    new_snippet_status_entities = [
        e for e in recorder.entities
        if isinstance(e, UserBriefingSnippetStatusSensor)
        and getattr(e, "subentry_id", None) == "snippet-2"
    ]
    assert len(new_snippet_entities) == 1
    assert len(new_snippet_status_entities) == 1
    # All calls after setup should have empty kwargs (flag stayed False)
    assert all(c == {} for c in recorder.calls[3:])  # calls[0:3] are profile sensors


def test_generated_at_and_snippet_status_entities_expose_dedicated_state() -> None:
    coordinator = _FakeCoordinator()
    generated_at = datetime(2026, 6, 29, 12, 0, tzinfo=UTC)
    snippet = SimpleNamespace(
        provider_key="calendar",
        status="warning",
        priority="required",
        scenario="busy",
        text="Busy day ahead",
    )
    coordinator.last_result = SimpleNamespace(
        generated_at=generated_at,
        summary_state="ready",
        snippets=[snippet],
    )
    coordinator._snippet_results["snippet-1"] = snippet
    entry = _FakeEntry({"snippet-1": _subentry("snippet-1", "Calendar")})

    generated_sensor = UserBriefingGeneratedAtSensor(coordinator, entry)
    snippet_sensor = UserBriefingSnippetSensor(
        coordinator, entry, entry.subentries["snippet-1"]
    )
    snippet_status_sensor = UserBriefingSnippetStatusSensor(
        coordinator, entry, entry.subentries["snippet-1"]
    )

    assert generated_sensor.native_value == generated_at
    assert snippet_status_sensor.native_value == "warning"
    assert snippet_status_sensor.name == "Alex Calendar Status"
    assert ATTR_GENERATED_AT not in snippet_sensor.extra_state_attributes
    assert snippet_sensor.extra_state_attributes == {
        "summary_state": "ready",
        "snippet_count": 1,
        "provider_key": "calendar",
        "priority": "required",
        "scenario": "busy",
    }


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
