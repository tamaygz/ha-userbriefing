"""Datamodels for User Briefing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class UserProfile:
    """Immutable and mutable user profile view."""

    user_key: str
    display_name: str
    locale: str
    dashboard_template: str
    dashboard_path: str | None = None
    default_delivery_mode: str = "dashboard"
    rendering_style: str = "friendly"


@dataclass(slots=True)
class ProviderMetadata:
    """Metadata exposed by a provider to the UI and runtime."""

    key: str
    name: str
    version: str
    provider_api_version: int
    supports_multiple_instances: bool = True
    supports_preview: bool = True
    supports_required_priority: bool = True
    supports_actions: bool = False
    supports_deep_link: bool = False
    supports_dashboard_card: bool = True
    supports_alerts: bool = False
    supports_phrase_overrides: bool = False
    default_order_group: str = "general"
    dependencies: tuple[str, ...] = ()


@dataclass(slots=True)
class DashboardFragment:
    """A reusable dashboard fragment declaration."""

    fragment_key: str
    provider_key: str
    title: str
    card_type: str
    entities: list[str] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    navigation_path: str | None = None
    layout_hint: str | None = None


@dataclass(slots=True)
class SnippetAction:
    """Provider-declared follow-up action metadata."""

    action_key: str
    title: str
    action_type: str = "future"
    payload: dict[str, Any] = field(default_factory=dict)


# Alert severities, ordered from most to least urgent for promotion sorting.
ALERT_SEVERITY_ORDER: tuple[str, ...] = ("critical", "warning", "info")


@dataclass(slots=True)
class AlertItem:
    """A structured attention item emitted by a provider.

    Alerts are distinct from a snippet's normal body text. The core composer is
    responsible for promoting alerts to the top of the briefing and ordering them
    by ``severity`` (see ``ALERT_SEVERITY_ORDER``).
    """

    alert_key: str
    provider_key: str
    severity: str
    title: str
    text: str
    source_label: str | None = None
    navigation_path: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SnippetResult:
    """Normalized snippet output."""

    provider_key: str
    instance_id: str
    status: str
    priority: str
    title: str
    text: str
    scenario: str
    data: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    actions: list[SnippetAction] = field(default_factory=list)
    alerts: list[AlertItem] = field(default_factory=list)


@dataclass(slots=True)
class SlotEntry:
    """In-memory slot written by the push_snippet service."""

    text: str
    title: str | None = None
    severity: str | None = None
    pushed_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    expires_at: datetime | None = None


@dataclass(slots=True)
class BriefingResult:
    """Final composed briefing output."""

    user_key: str
    generated_at: datetime
    summary_state: str
    snippets: list[SnippetResult] = field(default_factory=list)
    alerts: list[AlertItem] = field(default_factory=list)
    rendered_text: str = ""
    delivery_payloads: dict[str, Any] = field(default_factory=dict)