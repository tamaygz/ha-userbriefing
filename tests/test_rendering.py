"""Basic rendering tests."""

from datetime import UTC, datetime

from custom_components.user_briefing.models import AlertItem, BriefingResult, SnippetResult
from custom_components.user_briefing.rendering import render_briefing_text


def test_render_briefing_text_joins_non_empty_snippets() -> None:
    result = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="ready",
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="1",
                status="ok",
                priority="required",
                title="Calendar",
                text="First block",
                scenario="normal",
            ),
            SnippetResult(
                provider_key="weather_forecast",
                instance_id="2",
                status="ok",
                priority="optional",
                title="Weather",
                text="Second block",
                scenario="normal",
            ),
        ],
    )
    assert render_briefing_text(result) == "First block\n\nSecond block"


def test_render_briefing_text_puts_alerts_before_snippets() -> None:
    result = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="ready",
        alerts=[
            AlertItem(
                alert_key="calendar-standup",
                provider_key="calendar",
                severity="critical",
                title="Calendar conflict",
                text="Standup overlaps with a dentist appointment.",
                source_label="calendar.work",
            ),
            AlertItem(
                alert_key="weather-rain",
                provider_key="weather_forecast",
                severity="warning",
                title="Rain incoming",
                text="Heavy rain is expected before lunch.",
                source_label="weather.home",
            ),
        ],
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="1",
                status="ok",
                priority="required",
                title="Calendar",
                text="First block",
                scenario="normal",
            ),
            SnippetResult(
                provider_key="weather_forecast",
                instance_id="2",
                status="ok",
                priority="optional",
                title="Weather",
                text="Second block",
                scenario="normal",
            ),
        ],
    )

    assert render_briefing_text(result) == (
        "[CRITICAL] Calendar conflict: Standup overlaps with a dentist "
        "appointment. (calendar.work)\n\n"
        "[WARNING] Rain incoming: Heavy rain is expected before lunch. "
        "(weather.home)\n\n"
        "First block\n\n"
        "Second block"
    )