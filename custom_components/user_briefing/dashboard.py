"""Dashboard composition helpers for User Briefing."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
import yaml

from .const import (
    CONF_DASHBOARD_PATH,
    CONF_DASHBOARD_TEMPLATE,
    CONF_PROVIDER_KEY,
    DEFAULT_DASHBOARD_TEMPLATE,
    SUBENTRY_TYPE_SNIPPET,
)
from .models import ALERT_SEVERITY_ORDER, AlertItem, BriefingResult, DashboardFragment
from .providers.registry import create_provider, ensure_builtin_providers_loaded
from .subentries import get_config_subentry_data, iter_config_subentries


def build_dashboard_delivery_payload(
    hass: HomeAssistant,
    entry: ConfigEntry,
    briefing: BriefingResult,
) -> dict[str, Any]:
    """Build a generated dashboard payload for the latest briefing result."""
    ensure_builtin_providers_loaded()

    template_key = _get_entry_value(entry, CONF_DASHBOARD_TEMPLATE, DEFAULT_DASHBOARD_TEMPLATE)
    fragments = _build_dashboard_fragments(hass, entry, briefing)
    document = _build_dashboard_document(entry, briefing, fragments, template_key)
    return {
        "template": template_key,
        "path": document["views"][0]["path"],
        "fragments": [asdict(fragment) for fragment in fragments],
        "yaml": yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
    }


def _build_dashboard_fragments(
    hass: HomeAssistant,
    entry: ConfigEntry,
    briefing: BriefingResult,
) -> list[DashboardFragment]:
    profile_entities = _build_profile_entities(entry)
    fragments = [
        DashboardFragment(
            fragment_key="briefing_alerts",
            provider_key="core",
            title="Briefing Alerts",
            card_type="markdown",
            layout_hint="full-width",
        ),
        DashboardFragment(
            fragment_key="briefing_overview",
            provider_key="core",
            title="Briefing Overview",
            card_type="entities",
            entities=[
                profile_entities["briefing"],
                profile_entities["status"],
                profile_entities["generated_at"],
            ],
            layout_hint="full-width",
        ),
    ]

    subentries_by_id = {
        str(getattr(subentry, "subentry_id", "")): subentry
        for subentry in iter_config_subentries(entry, SUBENTRY_TYPE_SNIPPET)
    }

    for snippet in briefing.snippets:
        subentry = subentries_by_id.get(snippet.instance_id)
        snippet_title = getattr(subentry, "title", snippet.title)
        snippet_entities = _build_snippet_entities(entry, snippet_title)

        provider_fragments = []
        if subentry is not None:
            provider_config = get_config_subentry_data(subentry)
            provider_key = provider_config.get(CONF_PROVIDER_KEY)
            if isinstance(provider_key, str):
                provider_fragments = create_provider(hass, provider_key).build_dashboard_fragments(
                    snippet_entities["text"]
                )

        if not provider_fragments:
            provider_fragments = [
                DashboardFragment(
                    fragment_key=f"{snippet.provider_key}_{snippet.instance_id}",
                    provider_key=snippet.provider_key,
                    title=snippet.title,
                    card_type="entities",
                    entities=[snippet_entities["text"]],
                )
            ]

        for fragment in provider_fragments:
            entities = list(fragment.entities)
            if snippet_entities["status"] not in entities:
                entities.append(snippet_entities["status"])
            fragments.append(
                DashboardFragment(
                    fragment_key=fragment.fragment_key,
                    provider_key=fragment.provider_key,
                    title=fragment.title,
                    card_type=fragment.card_type,
                    entities=entities,
                    badges=list(fragment.badges),
                    navigation_path=fragment.navigation_path,
                    layout_hint=fragment.layout_hint,
                )
            )

    return fragments


def _build_dashboard_document(
    entry: ConfigEntry,
    briefing: BriefingResult,
    fragments: list[DashboardFragment],
    template_key: str,
) -> dict[str, Any]:
    cards = []
    alerts = _collect_alerts(briefing)
    profile_entities = _build_profile_entities(entry)

    for fragment in fragments:
        if fragment.fragment_key == "briefing_alerts":
            cards.append(_build_alert_card(alerts))
            continue

        if template_key == "compact" and fragment.fragment_key == "briefing_overview":
            cards.extend(
                [
                    {
                        "type": "markdown",
                        "title": "Briefing Summary",
                        "content": briefing.rendered_text or "No rendered briefing is available yet.",
                    },
                    {
                        "type": "entities",
                        "title": "Briefing Status",
                        "entities": [
                            profile_entities["status"],
                            profile_entities["generated_at"],
                        ],
                    },
                ]
            )
            continue

        cards.append(
            {
                "type": fragment.card_type,
                "title": fragment.title,
                "entities": fragment.entities,
            }
        )

    return {
        "title": f"{entry.title} User Briefing",
        "views": [
            {
                "title": entry.title,
                "path": _resolve_dashboard_path(entry),
                "cards": cards,
            }
        ],
    }


def _build_alert_card(alerts: list[AlertItem]) -> dict[str, str]:
    if not alerts:
        return {
            "type": "markdown",
            "title": "Briefing Alerts",
            "content": "No active briefing alerts.",
        }

    lines = []
    for alert in alerts:
        source = f" ({alert.source_label})" if alert.source_label else ""
        lines.append(f"- **{alert.severity.upper()}** {alert.title}: {alert.text}{source}")

    return {
        "type": "markdown",
        "title": "Briefing Alerts",
        "content": "\n".join(lines),
    }


def _collect_alerts(briefing: BriefingResult) -> list[AlertItem]:
    alerts = list(briefing.alerts)
    if not alerts:
        for snippet in briefing.snippets:
            alerts.extend(snippet.alerts)

    severity_order = {
        severity: index for index, severity in enumerate(ALERT_SEVERITY_ORDER)
    }
    return sorted(
        alerts,
        key=lambda alert: (
            severity_order.get(alert.severity, len(severity_order)),
            alert.provider_key,
            alert.alert_key,
        ),
    )


def _build_profile_entities(entry: ConfigEntry) -> dict[str, str]:
    return {
        "briefing": _sensor_entity_id(f"{entry.title} Briefing"),
        "status": _sensor_entity_id(f"{entry.title} Briefing Status"),
        "generated_at": _sensor_entity_id(f"{entry.title} Briefing Last Generated"),
    }


def _build_snippet_entities(entry: ConfigEntry, snippet_title: str) -> dict[str, str]:
    return {
        "text": _sensor_entity_id(f"{entry.title} {snippet_title}"),
        "status": _sensor_entity_id(f"{entry.title} {snippet_title} Status"),
    }


def _sensor_entity_id(name: str) -> str:
    return f"sensor.{slugify(name)}"


def _resolve_dashboard_path(entry: ConfigEntry) -> str:
    raw_path = _get_entry_value(entry, CONF_DASHBOARD_PATH, "")
    if isinstance(raw_path, str):
        stripped = raw_path.strip().strip("/")
        if stripped:
            return stripped
    return slugify(f"{entry.title} briefing")


def _get_entry_value(entry: ConfigEntry, key: str, default: Any) -> Any:
    options = getattr(entry, "options", {}) or {}
    if key in options:
        return options[key]

    data = getattr(entry, "data", {}) or {}
    return data.get(key, default)
