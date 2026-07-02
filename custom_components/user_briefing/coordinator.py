"""Coordinator for briefing generation orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLED,
    CONF_ORDER,
    CONF_PRIORITY,
    CONF_PROVIDER_KEY,
    CONF_TITLE_OVERRIDE,
    DEFAULT_ORDER,
    SNIPPET_COMMON_SETTING_KEYS,
    SUBENTRY_TYPE_SNIPPET,
)
from .dashboard import build_dashboard_delivery_payload
from .models import ALERT_SEVERITY_ORDER, AlertItem, BriefingResult, SlotEntry
from .notification import build_notification_payload
from .providers.registry import create_provider, ensure_builtin_providers_loaded
from .rendering import render_briefing_text
from .subentries import get_config_subentry_data, get_config_subentry_options, iter_config_subentries

_LOGGER = logging.getLogger(__name__)


def _sort_alerts(alerts: list[AlertItem]) -> list[AlertItem]:
    """Return alerts sorted by configured severity order."""
    severity_order = {
        severity: index for index, severity in enumerate(ALERT_SEVERITY_ORDER)
    }
    return sorted(
        alerts,
        key=lambda alert: severity_order.get(alert.severity.lower(), len(severity_order)),
    )


class UserBriefingCoordinator:
    """Coordinate provider execution and final briefing assembly."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.last_result: BriefingResult | None = None
        self.slot_store: dict[str, SlotEntry] = {}
        self._listeners: list[Callable[[], None]] = []

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener for result updates."""
        self._listeners.append(listener)

        def _remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove_listener

    def _notify_listeners(self) -> None:
        """Notify listeners of new results."""
        for listener in list(self._listeners):
            listener()

    def get_snippet_result(self, instance_id: str):
        """Return the last result for a snippet instance."""
        if self.last_result is None:
            return None
        for snippet in self.last_result.snippets:
            if snippet.instance_id == instance_id:
                return snippet
        return None

    async def async_preview(self, subentry_ids: set[str] | None = None) -> BriefingResult:
        """Generate a preview without mutating coordinator state."""
        return await self._async_build_result(subentry_ids=subentry_ids, persist=False)

    async def async_generate(self, subentry_ids: set[str] | None = None) -> BriefingResult:
        """Generate a briefing.

        The scaffold returns an empty normalized result until providers and subentry
        storage are wired.
        """
        return await self._async_build_result(subentry_ids=subentry_ids, persist=True)

    async def _async_build_result(
        self,
        subentry_ids: set[str] | None,
        persist: bool,
    ) -> BriefingResult:
        """Build a briefing result from configured snippet subentries."""
        ensure_builtin_providers_loaded()

        # Prune expired slot entries before dispatching to providers.
        now = datetime.now(tz=timezone.utc)
        expired = [
            sid
            for sid, entry in self.slot_store.items()
            if entry.expires_at is not None and entry.expires_at <= now
        ]
        for sid in expired:
            del self.slot_store[sid]

        snippets_with_order: list[tuple[int, str, object, dict[str, object]]] = []
        for subentry in iter_config_subentries(self.entry, SUBENTRY_TYPE_SNIPPET):
            subentry_id = getattr(subentry, "subentry_id", None)
            if subentry_ids is not None and subentry_id not in subentry_ids:
                continue

            subentry_options = get_config_subentry_options(subentry, SNIPPET_COMMON_SETTING_KEYS)

            if not subentry_options.get(CONF_ENABLED, True):
                continue

            snippets_with_order.append(
                (
                    int(subentry_options.get(CONF_ORDER, DEFAULT_ORDER)),
                    str(subentry_id or ""),
                    subentry,
                    subentry_options,
                )
            )

        snippets = []
        alerts = []
        for _order, _subentry_id, subentry, subentry_options in sorted(snippets_with_order, key=lambda item: (item[0], item[1])):
            subentry_id = getattr(subentry, "subentry_id", None)
            provider_config = get_config_subentry_data(subentry, SNIPPET_COMMON_SETTING_KEYS)
            provider_key = provider_config.get(CONF_PROVIDER_KEY)
            if not provider_key:
                continue

            provider = create_provider(self.hass, provider_key)
            try:
                collect_config = dict(provider_config)
                if provider_key == "custom_text" and subentry_id in self.slot_store:
                    collect_config["_slot_entry"] = self.slot_store[subentry_id]
                payload = await provider.async_collect(collect_config)
                snippet = provider.normalize(payload, subentry_id or provider_key)
                snippet.priority = subentry_options.get(CONF_PRIORITY, snippet.priority)
                snippet.title = subentry_options.get(CONF_TITLE_OVERRIDE) or snippet.title
                snippets.append(snippet)
                alerts.extend(snippet.alerts)
            except Exception as err:
                _LOGGER.exception("Provider %s failed during scaffold generation: %s", provider_key, err)

        result = BriefingResult(
            user_key=self.entry.data.get("user_key", self.entry.entry_id),
            generated_at=datetime.now(tz=timezone.utc),
            summary_state="ready" if snippets else "empty",
            snippets=snippets,
            alerts=_sort_alerts(alerts),
        )
        result.rendered_text = render_briefing_text(result)
        try:
            result.delivery_payloads["dashboard"] = build_dashboard_delivery_payload(
                self.hass,
                self.entry,
                result,
            )
        except Exception as err:  # pragma: no cover - defensive scaffolding
            _LOGGER.exception("Dashboard composition failed: %s", err)
        try:
            result.delivery_payloads["notification"] = build_notification_payload(
                self.entry,
                result,
            )
        except Exception as err:  # pragma: no cover - defensive scaffolding
            _LOGGER.exception("Notification payload build failed: %s", err)
        if persist:
            self.last_result = result
            self._notify_listeners()
        return result