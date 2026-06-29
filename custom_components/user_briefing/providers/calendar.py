"""Calendar provider scaffold."""

import voluptuous as vol
from homeassistant.helpers import selector

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class CalendarProvider(StubBriefingProvider):
    provider_key = "calendar"
    provider_name = "Calendar Summary"

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("source_type", default="calendar_entity"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["calendar_entity"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("source_ref"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                vol.Optional("summary_limit", default=3): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=20, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )