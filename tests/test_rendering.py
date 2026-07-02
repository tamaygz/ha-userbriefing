"""Basic rendering tests."""

from datetime import UTC, datetime

import pytest

from custom_components.user_briefing.models import AlertItem, BriefingResult, SnippetResult
from custom_components.user_briefing.rendering import (
    _collect_alerts,
    _load_phrase_bank,
    _select_phrase,
    render_alert_text,
    render_briefing_text,
    render_snippet_text,
)


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


# ---------------------------------------------------------------------------
# Phrase bank loading
# ---------------------------------------------------------------------------


def test_load_phrase_bank_returns_scenarios_for_known_provider() -> None:
    bank = _load_phrase_bank("calendar")
    assert "upcoming_events" in bank
    assert "empty" in bank
    assert "error" in bank
    assert isinstance(bank["upcoming_events"], list)
    assert len(bank["upcoming_events"]) > 0


def test_load_phrase_bank_returns_empty_dict_for_unknown_provider() -> None:
    bank = _load_phrase_bank("__no_such_provider__")
    assert bank == {}


def test_load_phrase_bank_caches_result() -> None:
    bank1 = _load_phrase_bank("weather_forecast")
    bank2 = _load_phrase_bank("weather_forecast")
    assert bank1 is bank2


# ---------------------------------------------------------------------------
# Phrase selection
# ---------------------------------------------------------------------------


def test_select_phrase_is_deterministic() -> None:
    phrases = ["option A", "option B", "option C"]
    result1 = _select_phrase(phrases, "inst-1", "upcoming_events")
    result2 = _select_phrase(phrases, "inst-1", "upcoming_events")
    assert result1 == result2


def test_select_phrase_varies_across_instance_ids() -> None:
    phrases = ["opt-0", "opt-1", "opt-2", "opt-3", "opt-4"]
    results = {_select_phrase(phrases, f"inst-{i}", "upcoming_events") for i in range(20)}
    assert len(results) > 1


def test_select_phrase_returns_valid_member() -> None:
    phrases = ["alpha", "beta", "gamma"]
    result = _select_phrase(phrases, "any-id", "any-scenario")
    assert result in phrases


# ---------------------------------------------------------------------------
# render_snippet_text — phrase bank integration
# ---------------------------------------------------------------------------


def test_render_snippet_text_uses_phrase_bank_template() -> None:
    """A snippet whose provider+scenario has a bank entry gets a bank phrase."""
    snippet = SnippetResult(
        provider_key="compliment",
        instance_id="compliment-1",
        status="ok",
        priority="optional",
        title="Compliment",
        text="fallback text",
        scenario="compliment",
        data={"compliment": "You're doing great!"},
    )
    rendered = render_snippet_text(snippet)
    assert rendered == "You're doing great!"


def test_render_snippet_text_interpolates_event_list() -> None:
    """Calendar upcoming_events phrases use {event_list} from snippet.data."""
    snippet = SnippetResult(
        provider_key="calendar",
        instance_id="cal-1",
        status="ok",
        priority="optional",
        title="Calendar",
        text="Upcoming events: Standup at 09:00.",
        scenario="upcoming_events",
        data={"events": [], "event_list": "Standup at 09:00", "event_count": 1},
    )
    rendered = render_snippet_text(snippet)
    assert "Standup at 09:00" in rendered


def test_render_snippet_text_interpolates_weather_summary() -> None:
    """Weather forecast_ready phrases use {summary} from snippet.data."""
    snippet = SnippetResult(
        provider_key="weather_forecast",
        instance_id="wx-1",
        status="ok",
        priority="optional",
        title="Weather",
        text="Forecast: sunny, high 25°.",
        scenario="forecast_ready",
        data={"forecast": [], "summary": "sunny, high 25°"},
    )
    rendered = render_snippet_text(snippet)
    assert "sunny, high 25°" in rendered


def test_render_snippet_text_interpolates_task_list() -> None:
    """Task summary tasks_ready phrases use {task_list} from snippet.data."""
    snippet = SnippetResult(
        provider_key="task_summary",
        instance_id="tasks-1",
        status="ok",
        priority="optional",
        title="Tasks",
        text="Open tasks: Buy milk.",
        scenario="tasks_ready",
        data={"items": [], "task_list": "Buy milk", "task_count": 1},
    )
    rendered = render_snippet_text(snippet)
    assert "Buy milk" in rendered


def test_render_snippet_text_falls_back_for_unknown_scenario() -> None:
    """Snippets with no bank entry for their scenario return snippet.text."""
    snippet = SnippetResult(
        provider_key="calendar",
        instance_id="cal-1",
        status="ok",
        priority="optional",
        title="Calendar",
        text="Plain fallback",
        scenario="__no_such_scenario__",
    )
    assert render_snippet_text(snippet) == "Plain fallback"


def test_render_snippet_text_falls_back_for_unknown_provider() -> None:
    """Snippets from providers with no bank file return snippet.text."""
    snippet = SnippetResult(
        provider_key="__no_such_provider__",
        instance_id="x-1",
        status="ok",
        priority="optional",
        title="X",
        text="No bank here",
        scenario="normal",
    )
    assert render_snippet_text(snippet) == "No bank here"


def test_render_snippet_text_falls_back_on_missing_context_key() -> None:
    """If interpolation fails (missing key), snippet.text is used."""
    snippet = SnippetResult(
        provider_key="calendar",
        instance_id="cal-1",
        status="ok",
        priority="optional",
        title="Calendar",
        text="fallback on error",
        scenario="upcoming_events",
        data={},  # event_list key is absent → KeyError during format_map
    )
    assert render_snippet_text(snippet) == "fallback on error"


def test_render_snippet_text_empty_scenario_uses_bank() -> None:
    """Calendar empty scenario returns a phrase from the bank (no interpolation needed)."""
    snippet = SnippetResult(
        provider_key="calendar",
        instance_id="cal-empty",
        status="empty",
        priority="optional",
        title="Calendar",
        text="No upcoming calendar events in the next 24 hours.",
        scenario="empty",
        data={"events": [], "event_count": 0},
    )
    rendered = render_snippet_text(snippet)
    # The bank provides multiple variations; all are non-empty strings.
    assert isinstance(rendered, str)
    assert len(rendered) > 0


@pytest.mark.parametrize("provider_key,scenario,data,expected_fragment", [
    (
        "weather_forecast",
        "forecast_ready",
        {"forecast": [], "summary": "cloudy, high 18°"},
        "cloudy, high 18°",
    ),
    (
        "task_summary",
        "tasks_ready",
        {"items": [], "task_list": "Pay bill; Call mom", "task_count": 2},
        "Pay bill; Call mom",
    ),
    (
        "compliment",
        "compliment",
        {"compliment": "Stay curious."},
        "Stay curious.",
    ),
])
def test_render_snippet_text_parametrized_providers(
    provider_key: str,
    scenario: str,
    data: dict,
    expected_fragment: str,
) -> None:
    snippet = SnippetResult(
        provider_key=provider_key,
        instance_id=f"{provider_key}-1",
        status="ok",
        priority="optional",
        title=provider_key,
        text="fallback",
        scenario=scenario,
        data=data,
    )
    rendered = render_snippet_text(snippet)
    assert expected_fragment in rendered


# ---------------------------------------------------------------------------
# render_alert_text — alert formatting (TEST-020)
# ---------------------------------------------------------------------------


def test_render_alert_text_formats_all_fields() -> None:
    """render_alert_text must produce [SEVERITY] title: text (source_label)."""
    alert = AlertItem(
        alert_key="wx-rain",
        provider_key="weather_forecast",
        severity="warning",
        title="Rain incoming",
        text="Heavy rain is expected before lunch.",
        source_label="weather.home",
    )
    assert render_alert_text(alert) == (
        "[WARNING] Rain incoming: Heavy rain is expected before lunch. (weather.home)"
    )


def test_render_alert_text_without_source_label() -> None:
    """render_alert_text must omit the trailing (source_label) when it is None."""
    alert = AlertItem(
        alert_key="cal-note",
        provider_key="calendar",
        severity="info",
        title="Calendar note",
        text="Team lunch is optional.",
        source_label=None,
    )
    assert render_alert_text(alert) == "[INFO] Calendar note: Team lunch is optional."


def test_render_alert_text_without_title() -> None:
    """render_alert_text must skip the title portion when title is blank."""
    alert = AlertItem(
        alert_key="sys-alert",
        provider_key="home_status",
        severity="critical",
        title="",
        text="Motion detected at front door.",
        source_label="binary_sensor.front_door",
    )
    assert render_alert_text(alert) == (
        "[CRITICAL]: Motion detected at front door. (binary_sensor.front_door)"
    )


def test_render_alert_text_severity_uppercased() -> None:
    """render_alert_text must uppercase the severity label regardless of input case."""
    alert = AlertItem(
        alert_key="a",
        provider_key="p",
        severity="warning",
        title="Test",
        text="Body.",
    )
    rendered = render_alert_text(alert)
    assert rendered.startswith("[WARNING]")


# ---------------------------------------------------------------------------
# _collect_alerts — alert collection and fallback (TEST-020)
# ---------------------------------------------------------------------------


def test_collect_alerts_uses_top_level_alerts_when_present() -> None:
    """_collect_alerts must return briefing.alerts when they are non-empty."""
    top_level_alert = AlertItem(
        alert_key="top",
        provider_key="p",
        severity="critical",
        title="Top",
        text="Top-level alert.",
    )
    snippet_alert = AlertItem(
        alert_key="snip",
        provider_key="p",
        severity="info",
        title="Snip",
        text="Snippet alert.",
    )
    briefing = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="ready",
        alerts=[top_level_alert],
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="1",
                status="ok",
                priority="optional",
                title="Calendar",
                text="",
                scenario="normal",
                alerts=[snippet_alert],
            )
        ],
    )
    result = _collect_alerts(briefing)
    assert len(result) == 1
    assert result[0].alert_key == "top"


def test_collect_alerts_falls_back_to_snippet_alerts_when_no_top_level() -> None:
    """_collect_alerts must gather snippet alerts when briefing.alerts is empty."""
    snip1_alert = AlertItem(
        alert_key="a1",
        provider_key="calendar",
        severity="warning",
        title="A1",
        text="From snippet 1.",
    )
    snip2_alert = AlertItem(
        alert_key="a2",
        provider_key="weather_forecast",
        severity="info",
        title="A2",
        text="From snippet 2.",
    )
    briefing = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="ready",
        alerts=[],
        snippets=[
            SnippetResult(
                provider_key="calendar",
                instance_id="1",
                status="ok",
                priority="optional",
                title="Calendar",
                text="",
                scenario="normal",
                alerts=[snip1_alert],
            ),
            SnippetResult(
                provider_key="weather_forecast",
                instance_id="2",
                status="ok",
                priority="optional",
                title="Weather",
                text="",
                scenario="normal",
                alerts=[snip2_alert],
            ),
        ],
    )
    result = _collect_alerts(briefing)
    assert {a.alert_key for a in result} == {"a1", "a2"}


def test_collect_alerts_sorts_by_severity() -> None:
    """_collect_alerts must return alerts sorted critical → warning → info."""
    briefing = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="ready",
        alerts=[
            AlertItem(alert_key="a-info", provider_key="p", severity="info", title="I", text=""),
            AlertItem(alert_key="a-critical", provider_key="p", severity="critical", title="C", text=""),
            AlertItem(alert_key="a-warning", provider_key="p", severity="warning", title="W", text=""),
        ],
    )
    result = _collect_alerts(briefing)
    assert [a.severity for a in result] == ["critical", "warning", "info"]


def test_collect_alerts_unknown_severity_sorted_last() -> None:
    """_collect_alerts must place unknown severity values after all known ones."""
    briefing = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="ready",
        alerts=[
            AlertItem(alert_key="a-unknown", provider_key="p", severity="notice", title="N", text=""),
            AlertItem(alert_key="a-warning", provider_key="p", severity="warning", title="W", text=""),
        ],
    )
    result = _collect_alerts(briefing)
    assert result[0].severity == "warning"
    assert result[1].severity == "notice"


def test_collect_alerts_empty_briefing_returns_empty() -> None:
    """_collect_alerts must return an empty list when there are no alerts anywhere."""
    briefing = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="empty",
        alerts=[],
        snippets=[],
    )
    assert _collect_alerts(briefing) == []


# ---------------------------------------------------------------------------
# render_briefing_text with unsorted alerts (TEST-020)
# ---------------------------------------------------------------------------


def test_render_briefing_text_sorts_unsorted_alerts_before_snippets() -> None:
    """render_briefing_text must sort alerts by severity AND place them before snippets.

    This ensures that even if alerts arrive in an arbitrary order they are
    promoted to the top and reordered critical → warning → info in the output.
    """
    briefing = BriefingResult(
        user_key="alice",
        generated_at=datetime.now(UTC),
        summary_state="ready",
        alerts=[
            AlertItem(
                alert_key="a-info",
                provider_key="weather_forecast",
                severity="info",
                title="Weather note",
                text="Mild breeze expected.",
                source_label="weather.home",
            ),
            AlertItem(
                alert_key="a-critical",
                provider_key="calendar",
                severity="critical",
                title="Schedule conflict",
                text="Two events overlap at 09:00.",
                source_label="calendar.work",
            ),
            AlertItem(
                alert_key="a-warning",
                provider_key="weather_forecast",
                severity="warning",
                title="Rain incoming",
                text="Heavy rain before noon.",
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
                text="Your first meeting is at 09:30.",
                scenario="normal",
            ),
        ],
    )
    rendered = render_briefing_text(briefing)

    # Alerts must appear before snippet body.
    critical_pos = rendered.index("[CRITICAL]")
    warning_pos = rendered.index("[WARNING]")
    info_pos = rendered.index("[INFO]")
    snippet_pos = rendered.index("Your first meeting is at 09:30.")

    assert critical_pos < warning_pos < info_pos < snippet_pos
