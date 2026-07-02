"""Dashboard composition tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.user_briefing.const import (
    DEFAULT_DASHBOARD_TEMPLATE,
    DOMAIN,
    SUBENTRY_TYPE_SNIPPET,
)
from custom_components.user_briefing.coordinator import UserBriefingCoordinator
from custom_components.user_briefing.dashboard import build_dashboard_delivery_payload
from custom_components.user_briefing.models import AlertItem, BriefingResult, SnippetResult


def _subentry(
    subentry_id: str,
    title: str,
    provider_key: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        subentry_id=subentry_id,
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        title=title,
        data={"provider_key": provider_key},
        options={"enabled": True, "order": 1},
    )


class _FakeEntityRegistry:
    def __init__(self, entity_ids: dict[tuple[str, str, str], str]) -> None:
        self._entity_ids = entity_ids

    def async_get_entity_id(self, domain: str, platform: str, unique_id: str) -> str | None:
        return self._entity_ids.get((domain, platform, unique_id))


def _entity_registry_for_entry(entry_id: str) -> _FakeEntityRegistry:
    return _FakeEntityRegistry(
        {
            ("sensor", DOMAIN, f"{entry_id}_summary"): "sensor.saved_briefing_summary",
            ("sensor", DOMAIN, f"{entry_id}_status"): "sensor.saved_briefing_status",
            ("sensor", DOMAIN, f"{entry_id}_generated_at"): "sensor.saved_briefing_generated_at",
            ("sensor", DOMAIN, f"{entry_id}_snippet-1"): "sensor.saved_calendar_text",
            ("sensor", DOMAIN, f"{entry_id}_snippet-1_status"): "sensor.saved_calendar_status",
        }
    )


def test_build_dashboard_delivery_payload_puts_alerts_first() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Alex",
        data={},
        options={"dashboard_template": DEFAULT_DASHBOARD_TEMPLATE, "dashboard_path": "/alex-briefing/"},
        subentries={"snippet-1": _subentry("snippet-1", "Calendar", "calendar")},
    )
    result = BriefingResult(
        user_key="alex",
        generated_at=datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
        summary_state="ready",
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="snippet-1",
                status="ok",
                priority="required",
                title="Calendar Summary",
                text="Upcoming events: Standup at 09:00.",
                scenario="upcoming_events",
                alerts=[
                    AlertItem(
                        alert_key="calendar-1",
                        provider_key="calendar",
                        severity="warning",
                        title="Calendar soon: Standup",
                        text="Standup starts at 09:00.",
                        source_label="calendar.work",
                    )
                ],
            )
        ],
    )

    with patch(
        "custom_components.user_briefing.dashboard.er.async_get",
        return_value=_entity_registry_for_entry(entry.entry_id),
    ):
        payload = build_dashboard_delivery_payload(SimpleNamespace(), entry, result)

    assert payload["template"] == "default"
    assert payload["path"] == "alex-briefing"
    yaml_output = payload["yaml"]
    assert "title: Briefing Alerts" in yaml_output
    assert "title: Briefing Overview" in yaml_output
    assert "title: Calendar Summary" in yaml_output
    assert yaml_output.index("title: Briefing Alerts") < yaml_output.index("title: Briefing Overview")
    assert yaml_output.index("title: Briefing Overview") < yaml_output.index("title: Calendar Summary")
    assert "sensor.saved_calendar_text" in yaml_output
    assert "sensor.saved_calendar_status" in yaml_output
    assert "Standup starts at 09:00." in yaml_output


def test_coordinator_preview_builds_end_to_end_dashboard_payload() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Alex",
        data={"user_key": "alex"},
        options={"dashboard_template": "compact"},
        subentries={"snippet-1": _subentry("snippet-1", "Compliment", "compliment")},
    )

    with patch(
        "custom_components.user_briefing.dashboard.er.async_get",
        return_value=_entity_registry_for_entry(entry.entry_id),
    ):
        result = asyncio.run(
            UserBriefingCoordinator(SimpleNamespace(), entry).async_preview()
        )

    dashboard_payload = result.delivery_payloads["dashboard"]
    assert dashboard_payload["template"] == "compact"
    assert "title: Briefing Alerts" in dashboard_payload["yaml"]
    assert "title: Briefing Summary" in dashboard_payload["yaml"]
    assert "title: Compliment" in dashboard_payload["yaml"]
    assert "sensor.saved_briefing_status" in dashboard_payload["yaml"]


def test_coordinator_preview_promotes_sorted_alerts_to_briefing_result() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Alex",
        data={"user_key": "alex"},
        options={"dashboard_template": "compact"},
        subentries={
            "snippet-1": SimpleNamespace(
                subentry_id="snippet-1",
                subentry_type=SUBENTRY_TYPE_SNIPPET,
                title="Calendar",
                data={"provider_key": "calendar"},
                options={"enabled": True, "order": 1},
            ),
            "snippet-2": SimpleNamespace(
                subentry_id="snippet-2",
                subentry_type=SUBENTRY_TYPE_SNIPPET,
                title="Weather",
                data={"provider_key": "weather_forecast"},
                options={"enabled": True, "order": 2},
            ),
        },
    )

    class _FakeProvider:
        def __init__(self, snippet: SnippetResult) -> None:
            self._snippet = snippet

        def prepare_collect_config(self, config: dict, runtime_ctx: dict) -> dict:
            return config

        async def async_collect(self, provider_config: dict[str, str]) -> dict[str, str]:
            return provider_config

        def normalize(self, payload: dict[str, str], instance_id: str) -> SnippetResult:
            return self._snippet

    providers = {
        "calendar": _FakeProvider(
            SnippetResult(
                provider_key="calendar",
                instance_id="snippet-1",
                status="ok",
                priority="required",
                title="Calendar",
                text="Calendar body.",
                scenario="normal",
                alerts=[
                    AlertItem(
                        alert_key="calendar-warning",
                        provider_key="calendar",
                        severity="warning",
                        title="Calendar warning",
                        text="Leave early for traffic.",
                        source_label="calendar.work",
                    ),
                    AlertItem(
                        alert_key="calendar-info",
                        provider_key="calendar",
                        severity="info",
                        title="Calendar note",
                        text="Team lunch is optional.",
                        source_label="calendar.work",
                    ),
                ],
            )
        ),
        "weather_forecast": _FakeProvider(
            SnippetResult(
                provider_key="weather_forecast",
                instance_id="snippet-2",
                status="ok",
                priority="optional",
                title="Weather",
                text="Weather body.",
                scenario="normal",
                alerts=[
                    AlertItem(
                        alert_key="weather-critical",
                        provider_key="weather_forecast",
                        severity="critical",
                        title="Weather alert",
                        text="Hail starts in 15 minutes.",
                        source_label="weather.home",
                    ),
                    AlertItem(
                        alert_key="weather-warning",
                        provider_key="weather_forecast",
                        severity="warning",
                        title="Weather caution",
                        text="Wind gusts are increasing.",
                        source_label="weather.home",
                    ),
                ],
            )
        ),
    }

    with (
        patch(
            "custom_components.user_briefing.coordinator.ensure_builtin_providers_loaded"
        ),
        patch(
            "custom_components.user_briefing.coordinator.create_provider",
            side_effect=lambda hass, provider_key: providers[provider_key],
        ),
        patch(
            "custom_components.user_briefing.coordinator.build_dashboard_delivery_payload",
            return_value={},
        ),
    ):
        result = asyncio.run(
            UserBriefingCoordinator(SimpleNamespace(), entry).async_preview()
        )

    assert [alert.alert_key for alert in result.alerts] == [
        "weather-critical",
        "calendar-warning",
        "weather-warning",
        "calendar-info",
    ]
    assert result.rendered_text == (
        "[CRITICAL] Weather alert: Hail starts in 15 minutes. (weather.home)\n\n"
        "[WARNING] Calendar warning: Leave early for traffic. (calendar.work)\n\n"
        "[WARNING] Weather caution: Wind gusts are increasing. (weather.home)\n\n"
        "[INFO] Calendar note: Team lunch is optional. (calendar.work)\n\n"
        "Calendar body.\n\n"
        "Weather body."
    )
