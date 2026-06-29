"""Entity base classes for User Briefing."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.helpers.entity import Entity

from .const import ATTR_GENERATED_AT, ATTR_SNIPPET_COUNT, ATTR_SUMMARY_STATE
from .models import BriefingResult
from .coordinator import UserBriefingCoordinator


class UserBriefingEntity(Entity):
    """Base entity for briefing-backed entities."""

    _remove_listener: Callable[[], None] | None = None

    def __init__(self, coordinator: UserBriefingCoordinator) -> None:
        self.coordinator = coordinator

    def set_briefing_result(self, briefing_result: BriefingResult) -> None:
        """Update the entity's current briefing result."""
        self.coordinator.last_result = briefing_result

    async def async_added_to_hass(self) -> None:
        """Register coordinator listener when added."""
        self._remove_listener = self.coordinator.async_add_listener(self._handle_coordinator_update)

    async def async_will_remove_from_hass(self) -> None:
        """Remove coordinator listener when removed."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    def _handle_coordinator_update(self) -> None:
        """Write state when the coordinator updates."""
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        """Return common attributes."""
        briefing_result = self.coordinator.last_result
        if briefing_result is None:
            return None

        return {
            ATTR_SUMMARY_STATE: briefing_result.summary_state,
            ATTR_GENERATED_AT: briefing_result.generated_at.isoformat(),
            ATTR_SNIPPET_COUNT: len(briefing_result.snippets),
        }