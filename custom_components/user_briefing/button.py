"""Button entities for User Briefing."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import UserBriefingCoordinator
from .entity import UserBriefingEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up User Briefing buttons for a config entry."""
    coordinator: UserBriefingCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            UserBriefingGenerateButton(coordinator, entry),
            UserBriefingDeliverButton(coordinator, entry),
        ]
    )


class UserBriefingGenerateButton(UserBriefingEntity, ButtonEntity):
    """Button that triggers briefing generation and updates entity state."""

    _attr_icon = "mdi:play-circle-outline"
    _attr_translation_key = "generate"

    def __init__(self, coordinator: UserBriefingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_generate"
        self._attr_name = f"{entry.title} Generate Briefing"

    async def async_press(self) -> None:
        """Generate (or regenerate) the briefing and update entity state."""
        await self.coordinator.async_generate()


class UserBriefingDeliverButton(UserBriefingEntity, ButtonEntity):
    """Button that triggers briefing delivery (currently stubbed)."""

    _attr_icon = "mdi:send-outline"
    _attr_translation_key = "deliver"

    def __init__(self, coordinator: UserBriefingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_deliver"
        self._attr_name = f"{entry.title} Deliver Briefing"

    async def async_press(self) -> None:
        """Deliver the current briefing (delivery channel is stubbed for now)."""
        result = self.coordinator.last_result
        if result is None:
            result = await self.coordinator.async_preview()
        notification_payload = result.delivery_payloads.get("notification")
        _LOGGER.debug(
            "Deliver pressed for %s — notification payload ready: %s; "
            "actual delivery is stubbed pending a target channel",
            self.coordinator.entry.entry_id,
            notification_payload is not None,
        )
