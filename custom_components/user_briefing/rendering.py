"""Rendering helpers for User Briefing."""

from __future__ import annotations

from .models import ALERT_SEVERITY_ORDER, AlertItem, BriefingResult, SnippetResult


def render_snippet_text(snippet: SnippetResult) -> str:
    """Return the snippet text.

    The scaffold keeps rendering intentionally simple until phrase assets are wired.
    """
    return snippet.text.strip()


def render_alert_text(alert: AlertItem) -> str:
    """Return the promoted alert text."""
    rendered = f"[{alert.severity.upper()}]"
    if alert.title.strip():
        rendered = f"{rendered} {alert.title.strip()}"
    if alert.text.strip():
        rendered = f"{rendered}: {alert.text.strip()}"

    if alert.source_label:
        rendered = f"{rendered} ({alert.source_label})"

    return rendered


def _collect_alerts(briefing: BriefingResult) -> list[AlertItem]:
    alerts = list(briefing.alerts)
    if not alerts:
        for snippet in briefing.snippets:
            alerts.extend(snippet.alerts)

        severity_order = {
            severity: index for index, severity in enumerate(ALERT_SEVERITY_ORDER)
        }
        alerts.sort(
            key=lambda alert: severity_order.get(alert.severity, len(severity_order))
        )

    return alerts


def render_briefing_text(briefing: BriefingResult) -> str:
    """Render a final briefing string from normalized snippets."""
    rendered_parts = [render_alert_text(alert) for alert in _collect_alerts(briefing)]
    rendered_parts.extend(
        render_snippet_text(snippet) for snippet in briefing.snippets
    )
    return "\n\n".join(part for part in rendered_parts if part)