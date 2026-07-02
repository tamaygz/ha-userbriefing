"""Rendering helpers for User Briefing."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from .models import ALERT_SEVERITY_ORDER, AlertItem, BriefingResult, SnippetResult

_PHRASES_DIR = Path(__file__).parent / "phrases"

# Cache of loaded phrase banks keyed by provider_key.
# A missing key means the bank has not been loaded yet.
# A key mapping to an empty dict means no phrase bank file exists for that provider.
_PHRASE_BANK_CACHE: dict[str, dict[str, list[str]]] = {}


def _load_phrase_bank(provider_key: str) -> dict[str, list[str]]:
    """Return the scenario→phrases mapping for *provider_key*, loading it once."""
    if provider_key not in _PHRASE_BANK_CACHE:
        path = _PHRASES_DIR / f"{provider_key}.yaml"
        bank: dict[str, list[str]] = {}
        if path.is_file():
            try:
                with path.open(encoding="utf-8") as fh:
                    raw: Any = yaml.safe_load(fh) or {}
            except (OSError, yaml.YAMLError):
                raw = {}
            scenarios = raw.get("scenarios") if isinstance(raw, dict) else {}
            if isinstance(scenarios, dict):
                for scenario, phrases in scenarios.items():
                    if isinstance(phrases, str):
                        bank[str(scenario)] = [phrases]
                    elif isinstance(phrases, list):
                        bank[str(scenario)] = [p for p in phrases if isinstance(p, str)]
        _PHRASE_BANK_CACHE[provider_key] = bank
    return _PHRASE_BANK_CACHE[provider_key]


def _select_phrase(phrases: list[str], instance_id: str, scenario: str) -> str:
    """Select a phrase deterministically from *phrases*.

    The selection is stable across runs: the same *instance_id* and *scenario*
    always produce the same phrase template, but distinct instances rotate through
    the available options so users see variety across snippets.
    """
    key = f"{instance_id}:{scenario}".encode()
    index = int(hashlib.sha256(key).hexdigest(), 16) % len(phrases)
    return phrases[index]


def render_snippet_text(snippet: SnippetResult) -> str:
    """Return the rendered snippet text.

    Phrase banks are consulted first. If a bank entry exists for the snippet's
    provider and scenario the selected template is interpolated with the snippet's
    data dict. Missing or broken interpolation falls back to the pre-computed
    ``snippet.text``.
    """
    bank = _load_phrase_bank(snippet.provider_key)
    scenario_phrases = bank.get(snippet.scenario, [])
    if scenario_phrases:
        template = _select_phrase(scenario_phrases, snippet.instance_id, snippet.scenario)
        try:
            return template.format_map(snippet.data).strip()
        except (KeyError, ValueError):
            pass
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
        key=lambda alert: severity_order.get(alert.severity.lower(), len(severity_order))
    )

    return alerts


def render_briefing_text(briefing: BriefingResult) -> str:
    """Render a final briefing string from normalized snippets."""
    rendered_parts = [render_alert_text(alert) for alert in _collect_alerts(briefing)]
    rendered_parts.extend(
        render_snippet_text(snippet) for snippet in briefing.snippets
    )
    return "\n\n".join(part for part in rendered_parts if part)