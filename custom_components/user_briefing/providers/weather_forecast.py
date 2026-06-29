"""Weather provider scaffold."""

import voluptuous as vol
from homeassistant.helpers import selector

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class WeatherForecastProvider(StubBriefingProvider):
    provider_key = "weather_forecast"
    provider_name = "Weather Forecast"

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("source_type", default="weather_entity"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["weather_entity"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("source_ref"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Optional("summary_limit", default=3): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=20, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )