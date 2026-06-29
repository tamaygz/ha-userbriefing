"""Dashboard composition tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from custom_components.user_briefing.const import DEFAULT_DASHBOARD_TEMPLATE, SUBENTRY_TYPE_SNIPPET
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


def test_build_dashboard_delivery_payload_puts_alerts_first() -> None:
    entry = SimpleNamespace(
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

    payload = build_dashboard_delivery_payload(SimpleNamespace(), entry, result)

    assert payload["template"] == "default"
    assert payload["path"] == "alex-briefing"
    yaml_output = payload["yaml"]
    assert "title: Briefing Alerts" in yaml_output
    assert "title: Briefing Overview" in yaml_output
    assert "title: Calendar Summary" in yaml_output
    assert yaml_output.index("title: Briefing Alerts") < yaml_output.index("title: Briefing Overview")
    assert yaml_output.index("title: Briefing Overview") < yaml_output.index("title: Calendar Summary")
    assert "sensor.alex_calendar" in yaml_output
    assert "sensor.alex_calendar_status" in yaml_output
    assert "Standup starts at 09:00." in yaml_output


def test_coordinator_preview_builds_end_to_end_dashboard_payload() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Alex",
        data={"user_key": "alex"},
        options={"dashboard_template": "compact"},
        subentries={"snippet-1": _subentry("snippet-1", "Compliment", "compliment")},
    )

    result = asyncio.run(
        UserBriefingCoordinator(SimpleNamespace(), entry).async_preview()
    )

    dashboard_payload = result.delivery_payloads["dashboard"]
    assert dashboard_payload["template"] == "compact"
    assert "title: Briefing Alerts" in dashboard_payload["yaml"]
    assert "title: Briefing Summary" in dashboard_payload["yaml"]
    assert "title: Compliment" in dashboard_payload["yaml"]
