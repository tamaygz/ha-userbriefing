"""Calendar provider scaffold."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.helpers import selector

from ..adapters.calendar import CalendarAdapter
from ..models import AlertItem, SnippetResult
from .base_stub import StubBriefingProvider
from .contracts import ProviderAdapter
from .registry import register_provider

_SOON_EVENT_WINDOW = timedelta(hours=1)


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
            parsed = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
            return parsed.astimezone().strftime("%H:%M")
        except ValueError:
            return raw_start

    raw_date = start.get("date")
    if raw_date:
        return raw_date
    return None


def _parse_event_start(event: dict) -> datetime | None:
    start = event.get("start") or {}
    raw_start = start.get("dateTime")
    if not raw_start:
        return None

    try:
        return datetime.fromisoformat(raw_start.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


def _build_alerts(
    events: list[dict],
    *,
    instance_id: str,
    provider_key: str,
    source_ref: object,
) -> list[AlertItem]:
    now = datetime.now().astimezone()
    alerts: list[AlertItem] = []
    for index, event in enumerate(events):
        start = _parse_event_start(event)
        if start is None or start < now or start - now > _SOON_EVENT_WINDOW:
            continue

        summary = str(event.get("summary") or "Untitled event")
        when = _format_event_time(event) or start.isoformat()
        alerts.append(
            AlertItem(
                alert_key=f"{instance_id}:event:{index}:starting_soon",
                provider_key=provider_key,
                severity="warning",
                title=f"Calendar soon: {summary}",
                text=f"{summary} starts at {when}.",
                source_label=source_ref if isinstance(source_ref, str) else None,
                meta={"start": start.isoformat()},
            )
        )

    return alerts


@register_provider
class CalendarProvider(StubBriefingProvider):
    provider_key = "calendar"
    provider_name = "Calendar Summary"
    supports_alerts = True
    source_type = "calendar_entity"
    summary_limit_default = 3

    def build_source_ref_selector(self):
        return selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar"))

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
                data={"events": [], "event_count": 0},
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
                data={"events": events, "event_count": 0},
                meta={"source_ref": source_ref},
            )

        summaries = []
        for event in visible_events:
            summary = event.get("summary") or "Untitled event"
            when = _format_event_time(event)
            summaries.append(f"{summary} at {when}" if when else str(summary))

        extra_count = max(0, len(events) - len(visible_events))
        extra_suffix = f" and {extra_count} more" if extra_count else ""
        event_list = "; ".join(summaries) + extra_suffix
        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="ok",
            priority="optional",
            title=self.describe().name,
            text=f"Upcoming events: {event_list}.",
            scenario="upcoming_events",
            data={"events": events, "event_list": event_list, "event_count": len(events)},
            meta={"source_ref": source_ref},
            alerts=_build_alerts(
                events,
                instance_id=instance_id,
                provider_key=self.describe().key,
                source_ref=source_ref,
            ),
        )