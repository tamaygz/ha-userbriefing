"""Notification payload helpers for User Briefing.

Builds structured payloads suitable for Home Assistant's ``notify`` service
without performing any actual delivery. The coordinator stores the result in
``BriefingResult.delivery_payloads["notification"]`` so automations or the
``deliver`` service can consume it without re-generating the briefing.

Delivery is intentionally left as a stub. The payload contract defined here
makes it straightforward to wire up a real delivery call in a future phase
(mobile app, TTS, email, etc.) without changing how the briefing is assembled.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .models import ALERT_SEVERITY_ORDER, AlertItem, BriefingResult

_MAX_MESSAGE_LENGTH = 1000

# Map severity names to HA-compatible notification importance/priority levels.
_SEVERITY_IMPORTANCE: dict[str, str] = {
    "critical": "high",
    "warning": "high",
    "info": "default",
}


def build_notification_payload(
    entry: ConfigEntry,
    briefing: BriefingResult,
) -> dict[str, Any]:
    """Build a notification payload for the briefing result.

    The returned dict mirrors the field shape accepted by Home Assistant's
    ``notify`` service so it can be passed directly once a delivery target is
    known. No delivery is performed here.

    Fields:
    - ``title``: human-readable notification title derived from the entry name
    - ``message``: rendered briefing text, truncated if necessary
    - ``target``: ``None`` — a delivery target must be set by the caller
    - ``data``: structured metadata for mobile/push notification features:
        - ``tag``: stable dedup and grouping key
        - ``channel``: Android notification channel identifier
        - ``importance``: Android importance level (``"high"`` or ``"default"``)
        - ``push``: iOS push hints (``thread-id``)
        - ``badge``: count of active alerts (useful for iOS badge overlay)
        - ``actions``: stub list for future actionable notification buttons
    """
    alerts = _collect_alerts(briefing)
    importance = _derive_importance(alerts)
    user_key = briefing.user_key

    message = briefing.rendered_text or "Your briefing is ready."
    if len(message) > _MAX_MESSAGE_LENGTH:
        message = message[: _MAX_MESSAGE_LENGTH - 1] + "…"

    return {
        "title": f"{entry.title} Briefing",
        "message": message,
        "target": None,
        "data": {
            "tag": f"user_briefing_{user_key}",
            "channel": "user_briefing",
            "importance": importance,
            "push": {
                "thread-id": f"user_briefing_{user_key}",
            },
            "badge": len(alerts),
            "actions": _build_actions(briefing),
        },
    }


def _collect_alerts(briefing: BriefingResult) -> list[AlertItem]:
    """Return a deduplicated, severity-ordered list of active alerts."""
    alerts: list[AlertItem] = list(briefing.alerts)
    if not alerts:
        for snippet in briefing.snippets:
            alerts.extend(snippet.alerts)

    severity_order = {
        severity: index for index, severity in enumerate(ALERT_SEVERITY_ORDER)
    }
    return sorted(
        alerts,
        key=lambda a: (
            severity_order.get(a.severity, len(severity_order)),
            a.provider_key,
            a.alert_key,
        ),
    )


def _derive_importance(alerts: list[AlertItem]) -> str:
    """Return the highest importance level implied by the active alerts."""
    for alert in alerts:
        level = _SEVERITY_IMPORTANCE.get(alert.severity)
        if level == "high":
            return "high"
    return "default"


def _build_actions(briefing: BriefingResult) -> list[dict[str, Any]]:
    """Return stub action buttons harvested from snippet action metadata.

    Each action carries enough context for a future delivery layer to build
    real Home Assistant actionable notification buttons. The list is capped so
    payloads stay within platform limits.
    """
    actions: list[dict[str, Any]] = []
    for snippet in briefing.snippets:
        for action in snippet.actions:
            if len(actions) >= 3:  # noqa: PLR2004 – common platform cap
                break
            actions.append(
                {
                    "action": action.action_key,
                    "title": action.title,
                    "action_type": action.action_type,
                }
            )
        if len(actions) >= 3:  # noqa: PLR2004
            break
    return actions
