"""Constants for the User Briefing integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "user_briefing"
PLATFORMS: Final = ("sensor",)

CONF_USER_KEY: Final = "user_key"
CONF_DISPLAY_NAME: Final = "display_name"
CONF_LOCALE: Final = "locale"
CONF_DASHBOARD_TEMPLATE: Final = "dashboard_template"
CONF_DASHBOARD_PATH: Final = "dashboard_path"
CONF_DEFAULT_DELIVERY_MODE: Final = "default_delivery_mode"
CONF_RENDERING_STYLE: Final = "rendering_style"
CONF_PROVIDER_KEY: Final = "provider_key"
CONF_SOURCE_REF: Final = "source_ref"
CONF_SOURCE_TYPE: Final = "source_type"
CONF_ENABLED: Final = "enabled"
CONF_ORDER: Final = "order"
CONF_PRIORITY: Final = "priority"
CONF_TITLE_OVERRIDE: Final = "title_override"
CONF_PROVIDER_OPTIONS: Final = "provider_options"

# Keys stored in subentry options that separate "how to present" from "what to collect".
# Used by coordinator and config flow to split subentry data from options across
# Home Assistant versions that may not support subentry options storage.
SNIPPET_COMMON_SETTING_KEYS: tuple[str, ...] = (
    CONF_ENABLED,
    CONF_ORDER,
    CONF_PRIORITY,
    CONF_TITLE_OVERRIDE,
)

CONF_CONFIG_ENTRY_ID: Final = "config_entry_id"
CONF_SUBENTRY_ID: Final = "subentry_id"
CONF_CUSTOM_TEXT_MODE: Final = "mode"
CONF_CUSTOM_TEXT_SLOT_LABEL: Final = "slot_label"
CONF_CUSTOM_TEXT_DEFAULT_TEXT: Final = "default_text"

CUSTOM_TEXT_MODE_SLOT: Final = "slot"
CUSTOM_TEXT_MODE_ENTITY: Final = "entity"

DEFAULT_LOCALE: Final = "en"
DEFAULT_DASHBOARD_TEMPLATE: Final = "default"
DEFAULT_DELIVERY_MODE: Final = "dashboard"
DEFAULT_RENDERING_STYLE: Final = "friendly"
DEFAULT_ENABLED: Final = True
DEFAULT_ORDER: Final = 100
DEFAULT_PRIORITY: Final = "optional"

OPTION_DELIVERY_DASHBOARD: Final = "dashboard"
OPTION_DELIVERY_NOTIFICATION: Final = "notification_stub"
OPTION_DELIVERY_VOICE: Final = "voice_future"

SUBENTRY_TYPE_SNIPPET: Final = "snippet"
PROVIDER_API_VERSION: Final = 1

SERVICE_GENERATE: Final = "generate"
SERVICE_PREVIEW: Final = "preview"
SERVICE_DELIVER: Final = "deliver"
SERVICE_REFRESH_SNIPPET: Final = "refresh_snippet"
SERVICE_PUSH_SNIPPET: Final = "push_snippet"
SERVICE_CLEAR_SNIPPET: Final = "clear_snippet"

ATTR_SUMMARY_STATE: Final = "summary_state"
ATTR_GENERATED_AT: Final = "generated_at"
ATTR_SNIPPET_COUNT: Final = "snippet_count"