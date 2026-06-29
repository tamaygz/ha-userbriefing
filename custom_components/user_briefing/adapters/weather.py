"""Weather adapter.

Consumes the existing Home Assistant ``weather`` integration via the
``weather.get_forecasts`` service response, with entity state as a fallback.
"""

from .base import HomeAssistantServiceAdapter


class WeatherAdapter(HomeAssistantServiceAdapter):
    """Adapter for weather-backed sources (``weather.get_forecasts``)."""