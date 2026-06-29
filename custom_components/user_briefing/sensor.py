"""Sensor entities for User Briefing."""

from __future__ import annotations

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
    entities: list[SensorEntity] = [
        UserBriefingSummarySensor(coordinator, entry),
        UserBriefingStatusSensor(coordinator, entry),
    ]
    for subentry in iter_config_subentries(entry, SUBENTRY_TYPE_SNIPPET):
        entities.append(UserBriefingSnippetSensor(coordinator, entry, subentry))
    async_add_entities(entities)


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
        subentry_id = getattr(subentry, "subentry_id", "unknown")
        title = getattr(subentry, "title", "Snippet")
        self._subentry_id = subentry_id
        self._attr_unique_id = f"{entry.entry_id}_{subentry_id}"
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