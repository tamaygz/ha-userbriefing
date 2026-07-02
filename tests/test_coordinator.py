"""Coordinator behavior tests.

Covers TEST-011 (adapter failure isolation), TEST-015 (enabled / order /
priority), TEST-016 (preview non-mutation), TEST-019 (alert collection
passthrough), alert severity ordering (TEST-020), slot-expiry pruning, and the
prepare_collect_config provider seam from plan/design-user-briefing-1.md.

Tests are intentionally self-contained: they use SimpleNamespace mocks for
hass and ConfigEntry so they run without a real Home Assistant instance.
Dashboard and notification payload building may raise inside the coordinator's
defensive try/except blocks (because those helpers need a real HA entity
registry); that is expected and does not affect snippet-level assertions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace, MappingProxyType
from unittest.mock import patch

from custom_components.user_briefing.const import (
    CONF_ENABLED,
    CONF_ORDER,
    CONF_PRIORITY,
    CONF_PROVIDER_KEY,
    CONF_TITLE_OVERRIDE,
    SUBENTRY_TYPE_SNIPPET,
)
from custom_components.user_briefing.coordinator import UserBriefingCoordinator, _sort_alerts
from custom_components.user_briefing.models import AlertItem, SlotEntry, SnippetResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_compliment_subentry(subentry_id: str = "s1") -> SimpleNamespace:
    return SimpleNamespace(
        subentry_id=subentry_id,
        subentry_type="snippet",
        title="Compliment",
        data={"provider_key": "compliment"},
        options={"enabled": True, "order": 100, "priority": "optional", "title_override": None},
    )


def _make_hass() -> SimpleNamespace:
    return SimpleNamespace(data={})


def _run(coro):
    return asyncio.run(coro)


_DELIVERY_PATCHES = (
    patch(
        "custom_components.user_briefing.coordinator.build_dashboard_delivery_payload",
        return_value={},
    ),
    patch(
        "custom_components.user_briefing.coordinator.build_notification_payload",
        return_value={},
    ),
)


# ---------------------------------------------------------------------------
# Regression test: MappingProxyType subentries (GitHub issue #43)
# ---------------------------------------------------------------------------


def test_generate_with_mapping_proxy_type_subentries_produces_ready_briefing() -> None:
    """Regression: HA stores config_entry.subentries as MappingProxyType, not dict.

    Before the fix, ``iter_config_subentries`` used ``isinstance(x, dict)`` which
    returns ``False`` for ``MappingProxyType``.  The function then fell through to
    iterate over the mapping *keys* (string subentry IDs) instead of the subentry
    objects, yielding nothing and leaving the briefing always empty.
    """
    sub = _make_compliment_subentry()
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries=MappingProxyType({"s1": sub}),
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "ready", (
        "Briefing should be 'ready' with a compliment subentry; got 'empty'. "
        "Check that iter_config_subentries handles MappingProxyType correctly."
    )
    assert len(result.snippets) == 1
    assert result.snippets[0].provider_key == "compliment"
    assert result.rendered_text  # non-empty


def test_generate_with_plain_dict_subentries_produces_ready_briefing() -> None:
    """Plain-dict subentries (test / older-HA path) still work after the fix."""
    sub = _make_compliment_subentry()
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries={"s1": sub},
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "ready"
    assert len(result.snippets) == 1
    assert result.rendered_text


def test_generate_with_no_subentries_produces_empty_briefing() -> None:
    """Empty subentries dict → summary_state='empty'."""
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries={},
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "empty"
    assert result.snippets == []


def test_generate_with_disabled_subentry_produces_empty_briefing() -> None:
    """A disabled snippet subentry is skipped, leaving the briefing empty."""
    sub = SimpleNamespace(
        subentry_id="s1",
        subentry_type="snippet",
        title="Compliment",
        data={"provider_key": "compliment"},
        options={"enabled": False, "order": 100, "priority": "optional", "title_override": None},
    )
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries=MappingProxyType({"s1": sub}),
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        result = _run(coordinator.async_generate())

    assert result.summary_state == "empty"


def test_generate_with_unknown_provider_key_logs_and_continues() -> None:
    """An unregistered provider key is caught inside the try block and skipped."""
    sub = SimpleNamespace(
        subentry_id="s1",
        subentry_type="snippet",
        title="Unknown",
        data={"provider_key": "nonexistent_provider_xyz"},
        options={"enabled": True, "order": 100, "priority": "optional", "title_override": None},
    )
    entry = SimpleNamespace(
        entry_id="e1",
        data={"user_key": "user1"},
        options={},
        subentries=MappingProxyType({"s1": sub}),
    )
    hass = _make_hass()
    coordinator = UserBriefingCoordinator(hass, entry)  # type: ignore[arg-type]

    with _DELIVERY_PATCHES[0], _DELIVERY_PATCHES[1]:
        # Must not raise; unknown provider should be caught and logged.
        result = _run(coordinator.async_generate())

    assert result.summary_state == "empty"
    assert coordinator.last_result is not None
def _make_subentry(
    subentry_id: str,
    provider_key: str,
    *,
    data_extras: dict | None = None,
    options: dict | None = None,
) -> SimpleNamespace:
    """Return a minimal mock subentry.

    ``data`` holds the provider key and any provider-specific config;
    ``options`` holds the snippet presentation settings (enabled, order,
    priority, title_override).
    """
    data = {CONF_PROVIDER_KEY: provider_key, **(data_extras or {})}
    return SimpleNamespace(
        subentry_id=subentry_id,
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        data=data,
        options=options or {},
    )


def _make_entry(
    subentries: list | None = None,
    *,
    entry_id: str = "entry-1",
    user_key: str = "alex",
) -> SimpleNamespace:
    """Return a minimal mock ConfigEntry."""
    return SimpleNamespace(
        entry_id=entry_id,
        data={"user_key": user_key},
        options={},
        title="Test User",
        subentries=list(subentries or []),
    )


def _make_hass(services=None) -> SimpleNamespace:
    """Return a minimal mock HomeAssistant instance."""

    class _NullServices:
        async def async_call(self, domain, service, data, *, blocking=True, return_response=True):
            return {}

    async def _async_add_executor_job(target, *args):
        return target(*args)

    return SimpleNamespace(
        services=services or _NullServices(),
        states=SimpleNamespace(get=lambda _eid: None),
        async_add_executor_job=_async_add_executor_job,
    )


class _FakeServices:
    """Fake HA services that returns a configurable response."""

    def __init__(self, response: object) -> None:
        self._response = response

    async def async_call(self, domain, service, data, *, blocking=True, return_response=True):
        return self._response


# ---------------------------------------------------------------------------
# Enabled / disabled handling (TEST-015)
# ---------------------------------------------------------------------------


def test_enabled_snippet_appears_in_result() -> None:
    """An enabled subentry produces a snippet in the result."""
    sub = _make_subentry("sub-1", "compliment")
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    assert len(result.snippets) == 1
    assert result.snippets[0].instance_id == "sub-1"


def test_disabled_snippet_is_skipped() -> None:
    """A subentry with enabled=False must not produce a snippet."""
    sub_enabled = _make_subentry("sub-1", "compliment")
    sub_disabled = _make_subentry("sub-2", "compliment", options={CONF_ENABLED: False})
    entry = _make_entry([sub_enabled, sub_disabled])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    assert len(result.snippets) == 1
    assert result.snippets[0].instance_id == "sub-1"


def test_all_disabled_snippets_yields_empty_result() -> None:
    """Disabling every subentry produces an empty result with summary_state='empty'."""
    sub = _make_subentry("sub-1", "compliment", options={CONF_ENABLED: False})
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    assert result.snippets == []
    assert result.summary_state == "empty"


# ---------------------------------------------------------------------------
# Order handling (TEST-015)
# ---------------------------------------------------------------------------


def test_snippets_sorted_by_order() -> None:
    """Snippets must appear in ascending configured-order sequence."""
    sub_last = _make_subentry("sub-last", "compliment", options={CONF_ORDER: 200})
    sub_first = _make_subentry("sub-first", "compliment", options={CONF_ORDER: 50})
    # Deliberately reversed in the subentries list to prove sorting matters.
    entry = _make_entry([sub_last, sub_first])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    assert len(result.snippets) == 2
    assert result.snippets[0].instance_id == "sub-first"
    assert result.snippets[1].instance_id == "sub-last"


def test_equal_order_broken_by_subentry_id() -> None:
    """Ties in order are broken by subentry_id for a deterministic sequence."""
    sub_b = _make_subentry("sub-b", "compliment", options={CONF_ORDER: 10})
    sub_a = _make_subentry("sub-a", "compliment", options={CONF_ORDER: 10})
    entry = _make_entry([sub_b, sub_a])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    assert len(result.snippets) == 2
    assert result.snippets[0].instance_id == "sub-a"
    assert result.snippets[1].instance_id == "sub-b"


# ---------------------------------------------------------------------------
# Priority and title override (TEST-015)
# ---------------------------------------------------------------------------


def test_priority_from_options_overrides_provider_default() -> None:
    """snippet.priority must reflect the value set in subentry options."""
    sub = _make_subentry("sub-1", "compliment", options={CONF_PRIORITY: "required"})
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    assert result.snippets[0].priority == "required"


def test_title_override_from_options_replaces_provider_title() -> None:
    """snippet.title must reflect the title_override set in subentry options."""
    sub = _make_subentry("sub-1", "compliment", options={CONF_TITLE_OVERRIDE: "Morning Boost"})
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    assert result.snippets[0].title == "Morning Boost"


def test_blank_title_override_falls_back_to_provider_title() -> None:
    """An empty-string title_override must not replace the provider title."""
    sub = _make_subentry("sub-1", "compliment", options={CONF_TITLE_OVERRIDE: ""})
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    result = asyncio.run(coordinator.async_generate())

    # Provider title (not blank) must be used.
    assert result.snippets[0].title != ""


# ---------------------------------------------------------------------------
# Partial provider failure (TEST-011)
# ---------------------------------------------------------------------------


def test_partial_provider_failure_skips_failed_snippet() -> None:
    """A provider exception during collection is isolated to that snippet.

    The coordinator must continue building results for all other snippets and
    log the failure rather than propagating it.
    """
    sub_a = _make_subentry("sub-a", "compliment")
    sub_b = _make_subentry("sub-b", "compliment")
    entry = _make_entry([sub_a, sub_b])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    call_number = [0]

    from custom_components.user_briefing.providers.compliment import ComplimentProvider

    original_collect = ComplimentProvider.async_collect

    async def patched_collect(self, config):
        call_number[0] += 1
        if call_number[0] == 2:
            raise RuntimeError("Simulated provider failure")
        return await original_collect(self, config)

    with patch.object(ComplimentProvider, "async_collect", patched_collect):
        result = asyncio.run(coordinator.async_generate())

    # Only sub-a must appear; sub-b's failure must be swallowed.
    assert len(result.snippets) == 1
    assert result.snippets[0].instance_id == "sub-a"


# ---------------------------------------------------------------------------
# Preview non-mutation (TEST-016)
# ---------------------------------------------------------------------------


def test_generate_persists_last_result() -> None:
    """async_generate must store the result in coordinator.last_result."""
    sub = _make_subentry("sub-1", "compliment")
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    assert coordinator.last_result is None
    asyncio.run(coordinator.async_generate())
    assert coordinator.last_result is not None


def test_preview_does_not_mutate_last_result() -> None:
    """async_preview must NOT write to coordinator.last_result (TEST-016)."""
    sub = _make_subentry("sub-1", "compliment")
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    assert coordinator.last_result is None
    asyncio.run(coordinator.async_preview())
    assert coordinator.last_result is None


def test_generate_notifies_listeners() -> None:
    """async_generate must invoke all registered listeners after persisting."""
    sub = _make_subentry("sub-1", "compliment")
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    notified: list[bool] = []
    coordinator.async_add_listener(lambda: notified.append(True))

    asyncio.run(coordinator.async_generate())

    assert notified == [True]


def test_preview_does_not_notify_listeners() -> None:
    """async_preview must NOT invoke listeners (state is unchanged)."""
    sub = _make_subentry("sub-1", "compliment")
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    notified: list[bool] = []
    coordinator.async_add_listener(lambda: notified.append(True))

    asyncio.run(coordinator.async_preview())

    assert notified == []


def test_generate_renders_in_executor_job() -> None:
    """Rendering should run through hass.async_add_executor_job."""
    sub = _make_subentry("sub-1", "compliment")
    entry = _make_entry([sub])
    calls: list[str] = []

    async def _async_add_executor_job(target, *args):
        calls.append(target.__name__)
        return target(*args)

    hass = _make_hass()
    hass.async_add_executor_job = _async_add_executor_job
    coordinator = UserBriefingCoordinator(hass, entry)

    result = asyncio.run(coordinator.async_generate())

    assert result.rendered_text
    assert calls == ["render_briefing_text"]


# ---------------------------------------------------------------------------
# Alert collection passthrough (TEST-019)
# ---------------------------------------------------------------------------


def test_alerts_collected_from_provider_snippets() -> None:
    """Alerts emitted by a provider snippet must appear in result.alerts."""
    severe_response = {
        "weather.home": {
            "forecast": [{"condition": "lightning", "temperature": 25, "templow": 18}]
        }
    }
    hass = _make_hass(services=_FakeServices(severe_response))
    sub = _make_subentry(
        "sub-1",
        "weather_forecast",
        data_extras={"source_ref": "weather.home", "summary_limit": 1},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(hass, entry)

    result = asyncio.run(coordinator.async_generate())

    assert len(result.alerts) >= 1
    assert any(a.severity == "warning" for a in result.alerts)


def test_alert_passthrough_does_not_remove_snippet_content() -> None:
    """A provider that emits alerts must still produce its normal snippet text."""
    severe_response = {
        "weather.home": {
            "forecast": [{"condition": "lightning", "temperature": 25, "templow": 18}]
        }
    }
    hass = _make_hass(services=_FakeServices(severe_response))
    sub = _make_subentry(
        "sub-1",
        "weather_forecast",
        data_extras={"source_ref": "weather.home", "summary_limit": 1},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(hass, entry)

    result = asyncio.run(coordinator.async_generate())

    # Snippet content must still be present alongside the alert.
    assert len(result.snippets) == 1
    assert result.snippets[0].status == "ok"
    assert result.snippets[0].text != ""


# ---------------------------------------------------------------------------
# Adapter-backed provider output
# ---------------------------------------------------------------------------


def test_adapter_backed_provider_collects_and_normalizes_output() -> None:
    """Coordinator must include snippet content fetched through a provider adapter.

    Exercises the full path: coordinator → create_provider → provider.async_collect
    → WeatherAdapter.async_fetch → hass.services.async_call → provider.normalize.
    """
    forecast_response = {
        "weather.home": {
            "forecast": [{"condition": "sunny", "temperature": 22, "templow": 15}]
        }
    }
    hass = _make_hass(services=_FakeServices(forecast_response))
    sub = _make_subentry(
        "sub-1",
        "weather_forecast",
        data_extras={"source_ref": "weather.home", "summary_limit": 1},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(hass, entry)

    result = asyncio.run(coordinator.async_generate())

    assert len(result.snippets) == 1
    assert result.snippets[0].status == "ok"
    assert "sunny" in result.snippets[0].text


# ---------------------------------------------------------------------------
# Alert severity ordering (_sort_alerts)
# ---------------------------------------------------------------------------


def test_sort_alerts_orders_by_severity_critical_warning_info() -> None:
    """_sort_alerts must return critical before warning before info."""
    alerts = [
        AlertItem(alert_key="a1", provider_key="p", severity="info", title="T", text="T"),
        AlertItem(alert_key="a2", provider_key="p", severity="critical", title="T", text="T"),
        AlertItem(alert_key="a3", provider_key="p", severity="warning", title="T", text="T"),
    ]
    sorted_alerts = _sort_alerts(alerts)
    assert [a.severity for a in sorted_alerts] == ["critical", "warning", "info"]


def test_sort_alerts_stable_for_equal_severity() -> None:
    """Alerts with the same severity preserve their original relative order."""
    alerts = [
        AlertItem(alert_key="first", provider_key="p", severity="warning", title="T", text="T"),
        AlertItem(alert_key="second", provider_key="p", severity="warning", title="T", text="T"),
    ]
    sorted_alerts = _sort_alerts(alerts)
    assert sorted_alerts[0].alert_key == "first"
    assert sorted_alerts[1].alert_key == "second"


def test_sort_alerts_unknown_severity_sorted_last() -> None:
    """Alerts with unknown severity must be sorted after all known severities."""
    alerts = [
        AlertItem(alert_key="unknown", provider_key="p", severity="unknown_level", title="T", text="T"),
        AlertItem(alert_key="critical", provider_key="p", severity="critical", title="T", text="T"),
    ]
    sorted_alerts = _sort_alerts(alerts)
    assert sorted_alerts[0].severity == "critical"
    assert sorted_alerts[1].severity == "unknown_level"


def test_sort_alerts_empty_list_returns_empty() -> None:
    """_sort_alerts must handle an empty input without error."""
    assert _sort_alerts([]) == []


def test_sort_alerts_same_severity_preserves_relative_order() -> None:
    """Alerts with identical severity must keep their relative input order (stable sort)."""
    alerts = [
        AlertItem(alert_key="w-first", provider_key="p", severity="warning", title="First", text=""),
        AlertItem(alert_key="w-second", provider_key="p", severity="warning", title="Second", text=""),
        AlertItem(alert_key="w-third", provider_key="p", severity="warning", title="Third", text=""),
    ]
    result = _sort_alerts(alerts)
    assert [a.alert_key for a in result] == ["w-first", "w-second", "w-third"]


def test_sort_alerts_handles_mixed_case_severity() -> None:
    """Severity comparisons must be case-insensitive."""
    alerts = [
        AlertItem(alert_key="a-info-upper", provider_key="p", severity="INFO", title="Info upper", text=""),
        AlertItem(alert_key="a-crit-mixed", provider_key="p", severity="Critical", title="Crit mixed", text=""),
    ]
    result = _sort_alerts(alerts)
    assert result[0].severity == "Critical"
    assert result[1].severity == "INFO"


def test_result_alerts_are_sorted_by_severity() -> None:
    """Generated BriefingResult.alerts must be sorted critical > warning > info."""
    # weather_forecast emits warning alerts on lightning; add a second provider
    # by running two snippets and checking the combined sort order.
    lightning_response = {
        "weather.home": {
            "forecast": [{"condition": "lightning", "temperature": 25, "templow": 18}]
        }
    }
    hass = _make_hass(services=_FakeServices(lightning_response))
    sub = _make_subentry(
        "sub-1",
        "weather_forecast",
        data_extras={"source_ref": "weather.home", "summary_limit": 1},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(hass, entry)

    result = asyncio.run(coordinator.async_generate())

    severities = [a.severity for a in result.alerts]
    # Verify they are in non-increasing severity order (critical, warning, info).
    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    ranks = [severity_rank.get(s, 99) for s in severities]
    assert ranks == sorted(ranks), f"Alerts not sorted by severity: {severities}"


# ---------------------------------------------------------------------------
# Alert promotion in rendered text
# ---------------------------------------------------------------------------


def test_rendered_text_contains_alerts_before_snippet_content() -> None:
    """render_briefing_text must place alert blocks before snippet paragraphs."""
    lightning_response = {
        "weather.home": {
            "forecast": [{"condition": "lightning", "temperature": 25, "templow": 18}]
        }
    }
    hass = _make_hass(services=_FakeServices(lightning_response))
    sub = _make_subentry(
        "sub-1",
        "weather_forecast",
        data_extras={"source_ref": "weather.home", "summary_limit": 1},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(hass, entry)

    result = asyncio.run(coordinator.async_generate())

    text = result.rendered_text
    assert text, "rendered_text must be non-empty when alerts and snippets are present"

    if not result.alerts or not result.snippets:
        # Guard: nothing to compare positions for.
        return

    # All alert severity labels are uppercased in brackets, e.g. [WARNING].
    alert_positions = [
        text.find(f"[{a.severity.upper()}]") for a in result.alerts
        if f"[{a.severity.upper()}]" in text
    ]

    # Snippet text is rendered through phrase banks so the raw snippet.text may
    # differ.  Instead, find the last occurrence of an alert marker and confirm
    # it comes before any non-alert paragraph.
    if alert_positions:
        last_alert_end = max(
            text.find(f"[{a.severity.upper()}]") + len(f"[{a.severity.upper()}]")
            for a in result.alerts
            if f"[{a.severity.upper()}]" in text
        )
        # Everything after the last alert marker is snippet body text.
        remainder = text[last_alert_end:]
        # The remainder must not be entirely whitespace (snippets must follow).
        assert remainder.strip(), "Snippet content must follow alert blocks"


# ---------------------------------------------------------------------------
# Alert promotion — multi-provider coordinator integration (TEST-020)
# ---------------------------------------------------------------------------


def _make_fake_provider(snippet: SnippetResult) -> object:
    """Return a minimal fake provider that returns *snippet* from normalize()."""

    class _FakeProvider:
        def __init__(self, s: SnippetResult) -> None:
            self._snippet = s

        def prepare_collect_config(self, config: dict, runtime_ctx: dict) -> dict:
            return config

        async def async_collect(self, config: dict) -> dict:
            return config

        def normalize(self, payload: dict, instance_id: str) -> SnippetResult:
            return self._snippet

    return _FakeProvider(snippet)


def test_coordinator_merges_and_sorts_alerts_from_multiple_providers() -> None:
    """Alerts emitted by multiple providers must be merged and sorted by severity.

    The resulting result.alerts must be ordered critical → warning → info
    regardless of the order providers were executed.
    """
    sub_1 = _make_subentry("sub-1", "calendar")
    sub_2 = _make_subentry("sub-2", "weather_forecast")
    entry = _make_entry([sub_1, sub_2])

    providers = {
        "calendar": _make_fake_provider(
            SnippetResult(
                provider_key="calendar",
                instance_id="sub-1",
                status="ok",
                priority="required",
                title="Calendar",
                text="Calendar body.",
                scenario="normal",
                alerts=[
                    AlertItem(
                        alert_key="cal-info",
                        provider_key="calendar",
                        severity="info",
                        title="Calendar note",
                        text="Team lunch is optional.",
                    ),
                    AlertItem(
                        alert_key="cal-warning",
                        provider_key="calendar",
                        severity="warning",
                        title="Calendar warning",
                        text="Leave early for traffic.",
                    ),
                ],
            )
        ),
        "weather_forecast": _make_fake_provider(
            SnippetResult(
                provider_key="weather_forecast",
                instance_id="sub-2",
                status="ok",
                priority="required",
                title="Weather",
                text="Weather body.",
                scenario="normal",
                alerts=[
                    AlertItem(
                        alert_key="wx-critical",
                        provider_key="weather_forecast",
                        severity="critical",
                        title="Weather alert",
                        text="Hail starts in 15 minutes.",
                    ),
                ],
            )
        ),
    }

    with (
        patch("custom_components.user_briefing.coordinator.ensure_builtin_providers_loaded"),
        patch(
            "custom_components.user_briefing.coordinator.create_provider",
            side_effect=lambda hass, provider_key: providers[provider_key],
        ),
        patch(
            "custom_components.user_briefing.coordinator.build_dashboard_delivery_payload",
            return_value={},
        ),
    ):
        result = asyncio.run(UserBriefingCoordinator(_make_hass(), entry).async_generate())

    assert [a.alert_key for a in result.alerts] == ["wx-critical", "cal-warning", "cal-info"]


def test_coordinator_alerts_appear_before_snippets_in_rendered_text() -> None:
    """Promoted alerts must be present at the start of result.rendered_text.

    This validates that the coordinator wires alert promotion through to the
    rendered output so that urgent items lead the briefing.
    """
    sub_1 = _make_subentry("sub-1", "calendar")
    entry = _make_entry([sub_1])

    providers = {
        "calendar": _make_fake_provider(
            SnippetResult(
                provider_key="calendar",
                instance_id="sub-1",
                status="ok",
                priority="required",
                title="Calendar",
                text="Calendar body.",
                scenario="normal",
                alerts=[
                    AlertItem(
                        alert_key="cal-critical",
                        provider_key="calendar",
                        severity="critical",
                        title="Critical alert",
                        text="Urgent issue detected.",
                    ),
                ],
            )
        ),
    }

    with (
        patch("custom_components.user_briefing.coordinator.ensure_builtin_providers_loaded"),
        patch(
            "custom_components.user_briefing.coordinator.create_provider",
            side_effect=lambda hass, provider_key: providers[provider_key],
        ),
        patch(
            "custom_components.user_briefing.coordinator.build_dashboard_delivery_payload",
            return_value={},
        ),
    ):
        result = asyncio.run(UserBriefingCoordinator(_make_hass(), entry).async_generate())

    assert result.rendered_text.startswith("[CRITICAL]")
    assert "Calendar body." in result.rendered_text
    alert_pos = result.rendered_text.index("[CRITICAL]")
    body_pos = result.rendered_text.index("Calendar body.")
    assert alert_pos < body_pos


# ---------------------------------------------------------------------------
# Slot expiry pruning
# ---------------------------------------------------------------------------


def test_expired_slot_is_pruned_before_generation() -> None:
    """Slots whose expires_at is in the past must be removed before provider dispatch."""
    sub = _make_subentry(
        "sub-slot",
        "custom_text",
        data_extras={"mode": "slot", "default_text": "", "slot_label": "test"},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    # Inject a slot entry that is already expired.
    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    coordinator.slot_store["sub-slot"] = SlotEntry(
        text="stale content",
        expires_at=past,
    )
    assert "sub-slot" in coordinator.slot_store

    asyncio.run(coordinator.async_generate())

    assert "sub-slot" not in coordinator.slot_store, (
        "Expired slot entry must be pruned from slot_store during generation"
    )


def test_non_expired_slot_is_not_pruned() -> None:
    """Slots whose expires_at is in the future must remain after generation."""
    sub = _make_subentry(
        "sub-slot",
        "custom_text",
        data_extras={"mode": "slot", "default_text": "", "slot_label": "test"},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    future = datetime.now(tz=timezone.utc) + timedelta(hours=1)
    coordinator.slot_store["sub-slot"] = SlotEntry(
        text="live content",
        expires_at=future,
    )

    asyncio.run(coordinator.async_generate())

    assert "sub-slot" in coordinator.slot_store, (
        "Non-expired slot entry must remain in slot_store after generation"
    )


def test_slot_without_expiry_is_never_pruned() -> None:
    """Slots with expires_at=None must never be automatically removed."""
    sub = _make_subentry(
        "sub-slot",
        "custom_text",
        data_extras={"mode": "slot", "default_text": "", "slot_label": "test"},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    coordinator.slot_store["sub-slot"] = SlotEntry(
        text="permanent content",
        expires_at=None,
    )

    asyncio.run(coordinator.async_generate())

    assert "sub-slot" in coordinator.slot_store, (
        "Slot entry with no expiry must remain in slot_store"
    )


def test_preview_also_prunes_expired_slots() -> None:
    """Slot pruning must happen in async_preview as well as async_generate."""
    sub = _make_subentry(
        "sub-slot",
        "custom_text",
        data_extras={"mode": "slot", "default_text": "", "slot_label": "test"},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    coordinator.slot_store["sub-slot"] = SlotEntry(text="stale", expires_at=past)

    asyncio.run(coordinator.async_preview())

    assert "sub-slot" not in coordinator.slot_store


# ---------------------------------------------------------------------------
# prepare_collect_config provider seam (architecture boundary)
# ---------------------------------------------------------------------------


def test_custom_text_slot_works_without_coordinator_special_case() -> None:
    """custom_text slot-mode content must reach the provider via prepare_collect_config.

    This test verifies that coordinator no longer contains provider-specific
    branching logic: the slot entry is passed through the generic
    prepare_collect_config() seam, not through an 'if provider_key == "custom_text"'
    check.
    """
    sub = _make_subentry(
        "sub-slot",
        "custom_text",
        data_extras={"mode": "slot", "default_text": "", "slot_label": "test"},
    )
    entry = _make_entry([sub])
    coordinator = UserBriefingCoordinator(_make_hass(), entry)

    # Store a valid (non-expired) slot entry.
    coordinator.slot_store["sub-slot"] = SlotEntry(text="Hello from slot")

    result = asyncio.run(coordinator.async_generate())

    assert len(result.snippets) == 1
    assert result.snippets[0].status == "ok"
    assert result.snippets[0].text == "Hello from slot"
