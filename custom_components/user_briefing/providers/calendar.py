"""Calendar provider scaffold."""

from __future__ import annotations

from datetime import datetime

import voluptuous as vol
from homeassistant.helpers import selector

from ..adapters.calendar import CalendarAdapter
from ..models import SnippetResult
from .base_stub import StubBriefingProvider
from .contracts import ProviderAdapter
from .registry import register_provider


def _extract_response_section(payload: dict, source_ref: str | None) -> dict:
    response = payload.get("response")
    if isinstance(response, dict):
        source_payload = response.get(source_ref) if source_ref else None
        if isinstance(source_payload, dict):
            return source_payload
        return response
    return {}


def _format_event_time(event: dict) -> str | None:
    start = event.get("start") or {}
    raw_start = start.get("dateTime")
    if raw_start:
        try:
            return datetime.fromisoformat(raw_start.replace("Z", "+00:00")).strftime("%H:%M")
        except ValueError:
            return raw_start

    raw_date = start.get("date")
    if raw_date:
        return raw_date
    return None


@register_provider
class CalendarProvider(StubBriefingProvider):
    provider_key = "calendar"
    provider_name = "Calendar Summary"

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("source_type", default="calendar_entity"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["calendar_entity"],
                        translation_key="provider_source_type",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("source_ref"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
                vol.Optional("summary_limit", default=3): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=20, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )

    def get_adapter(self) -> ProviderAdapter:
        return CalendarAdapter(self.hass)

    def normalize(self, payload: dict[str, object], instance_id: str) -> SnippetResult:
        source_ref = payload.get("source_ref")
        response_section = _extract_response_section(payload, source_ref if isinstance(source_ref, str) else None)
        raw_events = response_section.get("events", []) if isinstance(response_section, dict) else []
        events = raw_events if isinstance(raw_events, list) else []
        summary_limit = int(payload.get("summary_limit", 3))
        visible_events = events[:summary_limit]

        if not payload.get("available"):
            return SnippetResult(
                provider_key=self.describe().key,
                instance_id=instance_id,
                status="error",
                priority="optional",
                title=self.describe().name,
                text="Calendar data is unavailable right now.",
                scenario="error",
                data={"events": []},
                meta={"source_ref": source_ref},
            )

        if not visible_events:
            return SnippetResult(
                provider_key=self.describe().key,
                instance_id=instance_id,
                status="empty",
                priority="optional",
                title=self.describe().name,
                text="No upcoming calendar events in the next 24 hours.",
                scenario="empty",
                data={"events": events},
                meta={"source_ref": source_ref},
            )

        summaries = []
        for event in visible_events:
            summary = event.get("summary") or "Untitled event"
            when = _format_event_time(event)
            summaries.append(f"{summary} at {when}" if when else str(summary))

        extra_count = max(0, len(events) - len(visible_events))
        extra_suffix = f" and {extra_count} more" if extra_count else ""
        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="ok",
            priority="optional",
            title=self.describe().name,
            text=f"Upcoming events: {'; '.join(summaries)}{extra_suffix}.",
            scenario="upcoming_events",
            data={"events": events},
            meta={"source_ref": source_ref},
        )