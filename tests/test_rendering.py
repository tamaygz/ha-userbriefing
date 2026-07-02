"""Basic rendering tests."""

from datetime import UTC, datetime

import pytest

from custom_components.user_briefing.models import AlertItem, BriefingResult, SnippetResult
from custom_components.user_briefing.rendering import (
    _load_phrase_bank,
    _select_phrase,
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
