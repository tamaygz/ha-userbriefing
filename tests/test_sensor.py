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
    # Snippet entities are added in a single batch, without config_subentry_id,
    # so they all appear under the one profile device rather than per-subentry.
    assert add_entities.calls[1] == {}

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
    # snippet-2 entities also added in a single batch, no config_subentry_id
    assert add_entities.calls[2] == {}

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
