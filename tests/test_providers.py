"""Focused tests for real built-in provider behavior."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from custom_components.user_briefing.providers.calendar import CalendarProvider
from custom_components.user_briefing.providers.compliment import ComplimentProvider
from custom_components.user_briefing.providers.task_summary import TaskSummaryProvider
from custom_components.user_briefing.providers.weather_forecast import WeatherForecastProvider


class _FakeServices:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def async_call(self, domain, service, data, blocking=False, return_response=False):
        self.calls.append((domain, service, data))
        return self._response


def test_calendar_provider_collects_and_normalizes_events() -> None:
    services = _FakeServices({"calendar.work": {"events": [{"summary": "Standup", "start": {"dateTime": "2026-01-01T09:00:00+00:00"}}]}})
    provider = CalendarProvider(SimpleNamespace(services=services))

    payload = asyncio.run(provider.async_collect({"source_ref": "calendar.work", "summary_limit": 3}))
    snippet = provider.normalize(payload, "calendar-1")

    assert services.calls[0][0:2] == ("calendar", "get_events")
    assert services.calls[0][2]["entity_id"] == "calendar.work"
    assert snippet.status == "ok"
    assert "Standup at 09:00" in snippet.text


def test_calendar_provider_emits_alert_for_soon_event() -> None:
    provider = CalendarProvider(SimpleNamespace(services=_FakeServices({})))
    soon = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()

    snippet = provider.normalize(
        {
            "available": True,
            "source_ref": "calendar.work",
            "summary_limit": 3,
            "response": {
                "calendar.work": {
                    "events": [{"summary": "Standup", "start": {"dateTime": soon}}]
                }
            },
        },
        "calendar-1",
    )

    assert snippet.alerts
    assert snippet.alerts[0].severity == "warning"
    assert snippet.alerts[0].source_label == "calendar.work"


def test_weather_provider_collects_and_normalizes_forecast() -> None:
    services = _FakeServices({"weather.home": {"forecast": [{"condition": "sunny", "temperature": 25, "templow": 18}]}})
    provider = WeatherForecastProvider(SimpleNamespace(services=services))

    payload = asyncio.run(provider.async_collect({"source_ref": "weather.home", "summary_limit": 2}))
    snippet = provider.normalize(payload, "weather-1")

    assert services.calls[0][0:2] == ("weather", "get_forecasts")
    assert services.calls[0][2]["type"] == "daily"
    assert snippet.status == "ok"
    assert snippet.text == "Forecast: sunny, high 25°, low 18°."


def test_weather_provider_emits_alert_for_severe_conditions() -> None:
    provider = WeatherForecastProvider(SimpleNamespace(services=_FakeServices({})))

    snippet = provider.normalize(
        {
            "available": True,
            "source_ref": "weather.home",
            "summary_limit": 2,
            "response": {
                "weather.home": {
                    "forecast": [{"condition": "lightning", "temperature": 22, "templow": 17}]
                }
            },
        },
        "weather-1",
    )

    assert snippet.alerts
    assert snippet.alerts[0].severity == "warning"
    assert "lightning" in snippet.alerts[0].text


def test_task_summary_provider_collects_and_filters_open_tasks() -> None:
    services = _FakeServices(
        {
            "todo.home": {
                "items": [
                    {"summary": "Buy milk", "status": "needs_action"},
                    {"summary": "Done item", "status": "completed"},
                ]
            }
        }
    )
    provider = TaskSummaryProvider(SimpleNamespace(services=services))

    payload = asyncio.run(provider.async_collect({"source_ref": "todo.home", "summary_limit": 5}))
    snippet = provider.normalize(payload, "tasks-1")

    assert services.calls[0][0:2] == ("todo", "get_items")
    assert services.calls[0][2]["status"] == ["needs_action"]
    assert snippet.status == "ok"
    assert snippet.text == "Open tasks: Buy milk."


def test_task_summary_provider_emits_alerts_for_due_tasks() -> None:
    provider = TaskSummaryProvider(SimpleNamespace(services=_FakeServices({})))
    today = datetime.now(UTC).date().isoformat()

    snippet = provider.normalize(
        {
            "available": True,
            "source_ref": "todo.home",
            "summary_limit": 5,
            "response": {
                "todo.home": {
                    "items": [
                        {"summary": "Pay bill", "status": "needs_action", "due": "2000-01-01"},
                        {"summary": "Call mom", "status": "needs_action", "due": today},
                    ]
                }
            },
        },
        "tasks-1",
    )

    assert [alert.severity for alert in snippet.alerts] == ["critical", "warning"]
    assert snippet.alerts[0].source_label == "todo.home"


def test_compliment_provider_returns_local_phrase() -> None:
    provider = ComplimentProvider(SimpleNamespace())

    payload = asyncio.run(provider.async_collect({}))
    snippet = provider.normalize(payload, "compliment-1")

    assert snippet.status == "ok"
    assert snippet.scenario == "compliment"
    assert snippet.text == payload["compliment"]
