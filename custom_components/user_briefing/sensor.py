"""Sensor entities for User Briefing."""

from __future__ import annotations

import inspect
from collections.abc import Iterable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SUBENTRY_TYPE_SNIPPET
from .coordinator import UserBriefingCoordinator
from .entity import UserBriefingEntity
from .subentries import iter_config_subentries


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up User Briefing sensors for a config entry."""
    coordinator: UserBriefingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            UserBriefingSummarySensor(coordinator, entry),
            UserBriefingStatusSensor(coordinator, entry),
        ]
    )
    snippet_entity_manager = UserBriefingSnippetEntityManager(
        coordinator,
        entry,
        async_add_entities,
    )
    await snippet_entity_manager.async_sync_entities()
    entry.async_on_unload(
        entry.add_update_listener(snippet_entity_manager.async_handle_entry_update)
    )


class UserBriefingSnippetEntityManager:
    """Keep snippet entities in sync with config subentries."""

    def __init__(
        self,
        coordinator: UserBriefingCoordinator,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._async_add_entities = async_add_entities
        self._entities: dict[str, UserBriefingSnippetSensor] = {}
        try:
            parameters = inspect.signature(self._async_add_entities).parameters
        except (TypeError, ValueError):
            parameters = {}
        self._supports_config_subentry_id = "config_subentry_id" in parameters or any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )

    async def async_handle_entry_update(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Sync snippet entities when the parent entry changes."""
        del hass
        self._entry = entry
        await self.async_sync_entities()

        subentries: dict[str, object] = {}
        for subentry in iter_config_subentries(self._entry, SUBENTRY_TYPE_SNIPPET):
            raw_id = getattr(subentry, "subentry_id", None)
            if raw_id is None:
                continue
            subentries[str(raw_id)] = subentry

        removed_ids = set(self._entities) - set(subentries)
        for subentry_id in removed_ids:
            await self._entities.pop(subentry_id).async_remove()

        new_entities: list[UserBriefingSnippetSensor] = []
        for subentry_id, subentry in subentries.items():
            entity = self._entities.get(subentry_id)
            if entity is None:
                entity = UserBriefingSnippetSensor(
                    self._coordinator,
                    self._entry,
                    subentry,
                )
                self._entities[subentry_id] = entity
                new_entities.append(entity)
                continue

            entity.update_from_entry(self._entry, subentry)
            entity.async_write_ha_state()

        self._async_add_snippet_entities(new_entities)

    def _async_add_snippet_entities(
        self,
        entities: Iterable[UserBriefingSnippetSensor],
    ) -> None:
        """Add snippet entities with subentry association when supported."""
        for entity in entities:
            if self._supports_config_subentry_id:
                self._async_add_entities(
                    [entity],
                    config_subentry_id=entity.subentry_id,
                )
            else:
                self._async_add_entities([entity])


class UserBriefingSummarySensor(UserBriefingEntity, SensorEntity):
    """Sensor exposing the final rendered briefing."""

    _attr_icon = "mdi:text-box-outline"

    def __init__(self, coordinator: UserBriefingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_summary"
        self._attr_name = f"{entry.title} Briefing"

    @property
    def native_value(self) -> str | None:
        briefing_result = self.coordinator.last_result
        if briefing_result is None:
            return None
        return briefing_result.rendered_text


class UserBriefingStatusSensor(UserBriefingEntity, SensorEntity):
    """Sensor exposing the briefing status."""

    _attr_icon = "mdi:format-list-checks"

    def __init__(self, coordinator: UserBriefingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_name = f"{entry.title} Briefing Status"

    @property
    def native_value(self) -> str | None:
        briefing_result = self.coordinator.last_result
        if briefing_result is None:
            return None
        return briefing_result.summary_state


class UserBriefingSnippetSensor(UserBriefingEntity, SensorEntity):
    """Sensor exposing one snippet instance output."""

    _attr_icon = "mdi:view-list-outline"

    def __init__(self, coordinator: UserBriefingCoordinator, entry: ConfigEntry, subentry: object) -> None:
        super().__init__(coordinator)
        self._subentry_id = str(getattr(subentry, "subentry_id", "unknown"))
        self._attr_unique_id = f"{entry.entry_id}_{self._subentry_id}"
        self.update_from_entry(entry, subentry)

    @property
    def subentry_id(self) -> str:
        """Return the backing config subentry id."""
        return self._subentry_id

    def update_from_entry(self, entry: ConfigEntry, subentry: object) -> None:
        """Refresh entity metadata from the latest entry and subentry."""
        title = getattr(subentry, "title", "Snippet")
        self._attr_name = f"{entry.title} {title}"

    @property
    def native_value(self) -> str | None:
        snippet = self.coordinator.get_snippet_result(self._subentry_id)
        if snippet is None:
            return None
        return snippet.text

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        snippet = self.coordinator.get_snippet_result(self._subentry_id)
        if snippet is None:
            return super().extra_state_attributes

        attributes = super().extra_state_attributes or {}
        attributes.update(
            {
                "provider_key": snippet.provider_key,
                "status": snippet.status,
                "priority": snippet.priority,
                "scenario": snippet.scenario,
            }
        )
        return attributes