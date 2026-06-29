"""Tests for provider-specific configuration schemas."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from homeassistant.helpers import selector

from custom_components.user_briefing.providers.beach_conditions import BeachConditionsProvider
from custom_components.user_briefing.providers.calendar import CalendarProvider
from custom_components.user_briefing.providers.home_status import HomeStatusProvider
from custom_components.user_briefing.providers.mail_summary_stub import MailSummaryStubProvider
from custom_components.user_briefing.providers.news_headlines import NewsHeadlinesProvider
from custom_components.user_briefing.providers.task_summary import TaskSummaryProvider
from custom_components.user_briefing.providers.weather_forecast import WeatherForecastProvider
from custom_components.user_briefing.providers.wind_conditions import WindConditionsProvider


def test_service_backed_providers_hide_fixed_source_type() -> None:
    calendar = CalendarProvider(SimpleNamespace())
    weather = WeatherForecastProvider(SimpleNamespace())
    tasks = TaskSummaryProvider(SimpleNamespace())

    calendar_schema = calendar.build_config_schema().schema
    assert {getattr(key, "schema", key) for key in calendar_schema} == {"source_ref", "summary_limit"}
    assert isinstance(
        next(value for key, value in calendar_schema.items() if getattr(key, "schema", key) == "source_ref"),
        selector.EntitySelector,
    )
    assert calendar.validate_config({"source_ref": "calendar.work", "summary_limit": 4}) == {
        "source_ref": "calendar.work",
        "summary_limit": 4,
        "source_type": "calendar_entity",
    }

    weather_schema = weather.build_config_schema().schema
    assert {getattr(key, "schema", key) for key in weather_schema} == {"source_ref", "summary_limit"}
    assert isinstance(
        next(value for key, value in weather_schema.items() if getattr(key, "schema", key) == "source_ref"),
        selector.EntitySelector,
    )
    assert weather.validate_config({"source_ref": "weather.home", "summary_limit": 2}) == {
        "source_ref": "weather.home",
        "summary_limit": 2,
        "source_type": "weather_entity",
    }

    tasks_schema = tasks.build_config_schema().schema
    assert {getattr(key, "schema", key) for key in tasks_schema} == {"source_ref", "summary_limit"}
    assert isinstance(
        next(value for key, value in tasks_schema.items() if getattr(key, "schema", key) == "source_ref"),
        selector.EntitySelector,
    )
    assert tasks.validate_config({"source_ref": "todo.home", "summary_limit": 6}) == {
        "source_ref": "todo.home",
        "summary_limit": 6,
        "source_type": "todo_entity",
    }


def test_entity_backed_stub_providers_use_entity_selectors() -> None:
    beach = BeachConditionsProvider(SimpleNamespace())
    wind = WindConditionsProvider(SimpleNamespace())
    home_status = HomeStatusProvider(SimpleNamespace())

    for provider in (beach, wind, home_status):
        schema = provider.build_config_schema().schema
        assert {getattr(key, "schema", key) for key in schema} == {"source_ref"}
        assert isinstance(
            next(value for key, value in schema.items() if getattr(key, "schema", key) == "source_ref"),
            selector.EntitySelector,
        )
        assert provider.validate_config({"source_ref": "sensor.example"}) == {
            "source_ref": "sensor.example",
            "source_type": "entity",
        }


def test_integration_stub_providers_keep_only_relevant_fields() -> None:
    news = NewsHeadlinesProvider(SimpleNamespace())
    mail = MailSummaryStubProvider(SimpleNamespace())

    for provider in (news, mail):
        schema = provider.build_config_schema().schema
        assert {getattr(key, "schema", key) for key in schema} == {"source_ref", "summary_limit"}
        assert isinstance(
            next(value for key, value in schema.items() if getattr(key, "schema", key) == "source_ref"),
            selector.TextSelector,
        )
        assert provider.validate_config({"source_ref": "demo", "summary_limit": 7}) == {
            "source_ref": "demo",
            "summary_limit": 7,
            "source_type": "integration",
        }


def test_snippet_flow_strings_describe_provider_and_reconfigure_fields() -> None:
    strings = json.loads(
        Path("custom_components/user_briefing/strings.json").read_text(encoding="utf-8")
    )
    snippet_steps = strings["config_subentries"]["snippet"]["step"]

    assert set(snippet_steps["provider_config"]["data_description"]) == {
        "source_ref",
        "summary_limit",
    }
    assert set(snippet_steps["common"]["data_description"]) == {
        "enabled",
        "order",
        "priority",
        "title_override",
    }
    assert set(snippet_steps["reconfigure"]["data"]) == {
        "source_ref",
        "summary_limit",
        "enabled",
        "order",
        "priority",
        "title_override",
    }
    assert set(snippet_steps["reconfigure"]["data_description"]) == {
        "source_ref",
        "summary_limit",
        "enabled",
        "order",
        "priority",
        "title_override",
    }
