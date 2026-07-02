"""Notification payload helper tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.user_briefing.const import (
    DEFAULT_DASHBOARD_TEMPLATE,
    SUBENTRY_TYPE_SNIPPET,
)
from custom_components.user_briefing.coordinator import UserBriefingCoordinator
from custom_components.user_briefing.models import (
    AlertItem,
    BriefingResult,
    SnippetAction,
    SnippetResult,
)
from custom_components.user_briefing.notification import build_notification_payload


def _entry(user_key: str = "alex", title: str = "Alex") -> SimpleNamespace:
    return SimpleNamespace(
        entry_id="entry-1",
        title=title,
        data={"user_key": user_key},
        options={},
        subentries={},
    )


def _briefing(
    user_key: str = "alex",
    rendered_text: str = "Good morning, Alex.",
    snippets: list[SnippetResult] | None = None,
    alerts: list[AlertItem] | None = None,
) -> BriefingResult:
    return BriefingResult(
        user_key=user_key,
        generated_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        summary_state="ready",
        snippets=snippets or [],
        alerts=alerts or [],
        rendered_text=rendered_text,
    )


# ---------------------------------------------------------------------------
# build_notification_payload tests
# ---------------------------------------------------------------------------


def test_payload_shape() -> None:
    """The helper returns all required top-level and data keys."""
    payload = build_notification_payload(_entry(), _briefing())
    assert "title" in payload
    assert "message" in payload
    assert "target" in payload
    assert "data" in payload
    data = payload["data"]
    assert "tag" in data
    assert "channel" in data
    assert "importance" in data
    assert "push" in data
    assert "badge" in data
    assert "actions" in data


def test_title_includes_entry_name() -> None:
    entry = _entry(title="Maria")
    payload = build_notification_payload(entry, _briefing())
    assert payload["title"] == "Maria Briefing"


def test_message_is_rendered_text() -> None:
    briefing = _briefing(rendered_text="Today is sunny.")
    payload = build_notification_payload(_entry(), briefing)
    assert payload["message"] == "Today is sunny."


def test_message_fallback_when_empty() -> None:
    briefing = _briefing(rendered_text="")
    payload = build_notification_payload(_entry(), briefing)
    assert payload["message"] == "Your briefing is ready."


def test_message_truncated_when_too_long() -> None:
    long_text = "A" * 2000
    briefing = _briefing(rendered_text=long_text)
    payload = build_notification_payload(_entry(), briefing)
    assert len(payload["message"]) == 1000
    assert payload["message"].endswith("…")


def test_target_is_none() -> None:
    """target must always be None — delivery is stubbed."""
    payload = build_notification_payload(_entry(), _briefing())
    assert payload["target"] is None


def test_tag_uses_user_key() -> None:
    payload = build_notification_payload(_entry(user_key="bob"), _briefing(user_key="bob"))
    assert payload["data"]["tag"] == "user_briefing_bob"


def test_push_thread_id_uses_user_key() -> None:
    payload = build_notification_payload(_entry(user_key="carol"), _briefing(user_key="carol"))
    assert payload["data"]["push"]["thread-id"] == "user_briefing_carol"


def test_channel_constant() -> None:
    payload = build_notification_payload(_entry(), _briefing())
    assert payload["data"]["channel"] == "user_briefing"


# ---------------------------------------------------------------------------
# Alert-driven importance tests
# ---------------------------------------------------------------------------


def test_importance_default_when_no_alerts() -> None:
    payload = build_notification_payload(_entry(), _briefing())
    assert payload["data"]["importance"] == "default"


def test_importance_high_for_warning_alert() -> None:
    briefing = _briefing(
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="s1",
                status="ok",
                priority="optional",
                title="Calendar",
                text="Standup at 09:00.",
                scenario="upcoming_events",
                alerts=[
                    AlertItem(
                        alert_key="cal-1",
                        provider_key="calendar",
                        severity="warning",
                        title="Standup soon",
                        text="Standup starts at 09:00.",
                    )
                ],
            )
        ]
    )
    payload = build_notification_payload(_entry(), briefing)
    assert payload["data"]["importance"] == "high"


def test_importance_high_for_critical_alert() -> None:
    briefing = _briefing(
        alerts=[
            AlertItem(
                alert_key="alert-1",
                provider_key="weather_forecast",
                severity="critical",
                title="Storm warning",
                text="Heavy rain expected.",
            )
        ]
    )
    payload = build_notification_payload(_entry(), briefing)
    assert payload["data"]["importance"] == "high"


def test_importance_default_for_info_alert() -> None:
    briefing = _briefing(
        alerts=[
            AlertItem(
                alert_key="info-1",
                provider_key="compliment",
                severity="info",
                title="Tip",
                text="Stay hydrated.",
            )
        ]
    )
    payload = build_notification_payload(_entry(), briefing)
    assert payload["data"]["importance"] == "default"


# ---------------------------------------------------------------------------
# Badge count tests
# ---------------------------------------------------------------------------


def test_badge_zero_when_no_alerts() -> None:
    payload = build_notification_payload(_entry(), _briefing())
    assert payload["data"]["badge"] == 0


def test_badge_reflects_top_level_alert_count() -> None:
    briefing = _briefing(
        alerts=[
            AlertItem("a1", "calendar", "warning", "T1", "Text 1"),
            AlertItem("a2", "weather_forecast", "info", "T2", "Text 2"),
        ]
    )
    payload = build_notification_payload(_entry(), briefing)
    assert payload["data"]["badge"] == 2


def test_badge_reflects_snippet_alerts_when_no_top_level() -> None:
    briefing = _briefing(
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="s1",
                status="ok",
                priority="optional",
                title="Calendar",
                text="Today: nothing.",
                scenario="empty",
                alerts=[
                    AlertItem("a1", "calendar", "warning", "Title", "Body"),
                ],
            )
        ]
    )
    payload = build_notification_payload(_entry(), briefing)
    assert payload["data"]["badge"] == 1


# ---------------------------------------------------------------------------
# Actions stub tests
# ---------------------------------------------------------------------------


def test_actions_empty_when_no_snippet_actions() -> None:
    payload = build_notification_payload(_entry(), _briefing())
    assert payload["data"]["actions"] == []


def test_actions_populated_from_snippet_actions() -> None:
    briefing = _briefing(
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="s1",
                status="ok",
                priority="optional",
                title="Calendar",
                text="Standup at 09:00.",
                scenario="upcoming_events",
                actions=[
                    SnippetAction(
                        action_key="open_calendar",
                        title="Open calendar",
                        action_type="future",
                    )
                ],
            )
        ]
    )
    payload = build_notification_payload(_entry(), briefing)
    assert len(payload["data"]["actions"]) == 1
    assert payload["data"]["actions"][0]["action"] == "open_calendar"
    assert payload["data"]["actions"][0]["title"] == "Open calendar"


def test_actions_capped_at_three() -> None:
    actions = [
        SnippetAction(action_key=f"act{i}", title=f"Action {i}", action_type="future")
        for i in range(5)
    ]
    briefing = _briefing(
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="s1",
                status="ok",
                priority="optional",
                title="Calendar",
                text="...",
                scenario="normal",
                actions=actions,
            )
        ]
    )
    payload = build_notification_payload(_entry(), briefing)
    assert len(payload["data"]["actions"]) == 3


# ---------------------------------------------------------------------------
# Coordinator integration: notification payload appears in delivery_payloads
# ---------------------------------------------------------------------------


def _subentry(subentry_id: str, title: str, provider_key: str) -> SimpleNamespace:
    return SimpleNamespace(
        subentry_id=subentry_id,
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        title=title,
        data={"provider_key": provider_key},
        options={},
    )


class _FakeEntityRegistry:
    def async_get_entity_id(self, domain: str, platform: str, unique_id: str) -> str | None:
        return None


def test_coordinator_preview_includes_notification_payload() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Alex",
        data={"user_key": "alex"},
        options={"dashboard_template": DEFAULT_DASHBOARD_TEMPLATE},
        subentries={"snippet-1": _subentry("snippet-1", "Compliment", "compliment")},
    )

    with patch(
        "custom_components.user_briefing.dashboard.er.async_get",
        return_value=_FakeEntityRegistry(),
    ):
        result = asyncio.run(
            UserBriefingCoordinator(SimpleNamespace(), entry).async_preview()
        )

    assert "notification" in result.delivery_payloads
    notification = result.delivery_payloads["notification"]
    assert notification["title"] == "Alex Briefing"
    assert notification["target"] is None
    assert "data" in notification
