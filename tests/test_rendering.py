"""Basic rendering tests."""

from datetime import datetime

from custom_components.user_briefing.models import BriefingResult, SnippetResult
from custom_components.user_briefing.rendering import render_briefing_text


def test_render_briefing_text_joins_non_empty_snippets() -> None:
    result = BriefingResult(
        user_key="alice",
        generated_at=datetime.utcnow(),
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