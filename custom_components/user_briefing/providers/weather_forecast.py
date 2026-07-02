"""Weather provider scaffold."""

from __future__ import annotations

from ..models import AlertItem, SnippetResult
from homeassistant.helpers import selector

from ..adapters.weather import WeatherAdapter
from .base_stub import StubBriefingProvider
from .contracts import ProviderAdapter
from .registry import register_provider

_SEVERE_CONDITIONS = {
    "exceptional",
    "hail",
    "lightning",
    "lightning-rainy",
    "pouring",
    "snowy-rainy",
    "windy",
    "windy-variant",
}


def _extract_response_section(payload: dict, source_ref: str | None) -> dict:
    response = payload.get("response")
    if isinstance(response, dict):
        source_payload = response.get(source_ref) if source_ref else None
        if isinstance(source_payload, dict):
            return source_payload
        return response
    return {}


def _format_temperature(value: object) -> str | None:
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return f"{value}°"
    return None


def _normalize_condition(value: object) -> str:
    condition = str(value or "unknown").replace("_", " ").replace("-", " ")
    return " ".join(condition.split())


def _describe_forecast(forecast: dict, index: int) -> str:
    day_label = "Today" if index == 0 else "Tomorrow" if index == 1 else "Later"
    condition = _normalize_condition(forecast.get("condition"))
    high = _format_temperature(forecast.get("temperature"))
    low = _format_temperature(forecast.get("templow"))

    if high and low:
        return f"{day_label} looks {condition} with a high of {high} and a low of {low}."
    if high:
        return f"{day_label} looks {condition} with highs near {high}."
    if low:
        return f"{day_label} looks {condition} with lows near {low}."
    return f"{day_label} looks {condition}."


def _build_focus_sentence(forecast_items: list[dict]) -> str | None:
    if not forecast_items:
        return None

    today = forecast_items[0]
    condition = str(today.get("condition") or "").lower()
    normalized_condition = _normalize_condition(condition)

    if condition in _SEVERE_CONDITIONS:
        return f"Heads up: severe {normalized_condition} conditions are possible today."

    precipitation_probability = today.get("precipitation_probability")
    if isinstance(precipitation_probability, float) and precipitation_probability.is_integer():
        precipitation_probability = int(precipitation_probability)
    if isinstance(precipitation_probability, (int, float)) and precipitation_probability >= 70:
        precip_label = "Rain" if "rain" in normalized_condition else "Snow" if "snow" in normalized_condition else "Precipitation"
        return f"{precip_label} is likely today ({precipitation_probability}%)."

    return None


def _build_alerts(
    forecast_items: list[dict],
    *,
    instance_id: str,
    provider_key: str,
    source_ref: object,
) -> list[AlertItem]:
    alerts: list[AlertItem] = []
    for index, forecast in enumerate(forecast_items):
        condition = str(forecast.get("condition") or "").lower()
        precipitation_probability = forecast.get("precipitation_probability")
        if isinstance(precipitation_probability, float) and precipitation_probability.is_integer():
            precipitation_probability = int(precipitation_probability)

        if condition in _SEVERE_CONDITIONS:
            alerts.append(
                AlertItem(
                    alert_key=f"{instance_id}:forecast:{index}:condition",
                    provider_key=provider_key,
                    severity="warning",
                    title="Weather alert",
                    text=f"Watch for severe {_normalize_condition(condition)} conditions."
                    source_label=source_ref if isinstance(source_ref, str) else None,
                    meta={"condition": condition},
                )
            )
            continue

        if isinstance(precipitation_probability, (int, float)) and precipitation_probability >= 70:
            alerts.append(
                AlertItem(
                    alert_key=f"{instance_id}:forecast:{index}:precipitation",
                    provider_key=provider_key,
                    severity="warning",
                    title="Weather alert",
                    text=f"High rain chance ahead ({precipitation_probability}%).",
                    source_label=source_ref if isinstance(source_ref, str) else None,
                    meta={"precipitation_probability": precipitation_probability},
                )
            )

    return alerts


@register_provider
class WeatherForecastProvider(StubBriefingProvider):
    provider_key = "weather_forecast"
    provider_name = "Weather Forecast"
    supports_alerts = True
    source_type = "weather_entity"
    summary_limit_default = 3

    def build_source_ref_selector(self):
        return selector.EntitySelector(selector.EntitySelectorConfig(domain="weather"))

    def get_adapter(self) -> ProviderAdapter:
        return WeatherAdapter(self.hass)

    def normalize(self, payload: dict[str, object], instance_id: str) -> SnippetResult:
        source_ref = payload.get("source_ref")
        response_section = _extract_response_section(payload, source_ref if isinstance(source_ref, str) else None)
        raw_forecast = response_section.get("forecast", []) if isinstance(response_section, dict) else []
        forecast_items = raw_forecast if isinstance(raw_forecast, list) else []
        summary_limit = int(payload.get("summary_limit", 3))
        visible_forecast = forecast_items[:summary_limit]

        if not payload.get("available"):
            return SnippetResult(
                provider_key=self.describe().key,
                instance_id=instance_id,
                status="error",
                priority="optional",
                title=self.describe().name,
                text="Weather forecast data is unavailable right now.",
                scenario="error",
                data={"forecast": []},
                meta={"source_ref": source_ref},
            )

        if not visible_forecast:
            return SnippetResult(
                provider_key=self.describe().key,
                instance_id=instance_id,
                status="empty",
                priority="optional",
                title=self.describe().name,
                text="No weather forecast is available right now.",
                scenario="empty",
                data={"forecast": forecast_items},
                meta={"source_ref": source_ref},
            )

        segments = [_describe_forecast(item, index) for index, item in enumerate(visible_forecast)]
        focus_sentence = _build_focus_sentence(visible_forecast)
        summary = " ".join(segments + ([focus_sentence] if focus_sentence else []))
        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="ok",
            priority="optional",
            title=self.describe().name,
            text=summary,
            scenario="forecast_ready",
            data={"forecast": forecast_items, "summary": summary, "focus_sentence": focus_sentence or ""},
            meta={"source_ref": source_ref},
            alerts=_build_alerts(
                forecast_items,
                instance_id=instance_id,
                provider_key=self.describe().key,
                source_ref=source_ref,
            ),
        )