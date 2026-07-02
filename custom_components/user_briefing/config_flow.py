"""Config flow for User Briefing."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

try:
    from homeassistant.data_entry_flow import section
except ImportError:  # pragma: no cover - compatibility for older local test envs
    def section(schema, _options=None):
        """Fallback passthrough for older Home Assistant versions."""
        return schema

try:
    from homeassistant.config_entries import OptionsFlowWithReload
except ImportError:  # pragma: no cover - compatibility for older local test envs
    from homeassistant.config_entries import OptionsFlow as OptionsFlowWithReload

try:
    from homeassistant.config_entries import ConfigSubentryFlow
except ImportError:  # pragma: no cover - compatibility for older local test envs
    class ConfigSubentryFlow:  # type: ignore[override]
        """Compatibility placeholder for older Home Assistant versions.

        The project targets newer Home Assistant builds that provide real config
        subentry flows. This placeholder keeps local test collection importable in
        environments where the newer API is not available yet.
        """

        pass

from .const import (
    CONF_CUSTOM_TEXT_MODE,
    CONF_DASHBOARD_PATH,
    CONF_DASHBOARD_TEMPLATE,
    CONF_DEFAULT_DELIVERY_MODE,
    CONF_DISPLAY_NAME,
    CONF_ENABLED,
    CONF_LOCALE,
    CONF_ORDER,
    CONF_PRIORITY,
    CONF_PROVIDER_KEY,
    CONF_RENDERING_STYLE,
    CONF_SOURCE_REF,
    CONF_SOURCE_TYPE,
    CONF_TITLE_OVERRIDE,
    CONF_USER_KEY,
    CUSTOM_TEXT_MODE_ENTITY,
    CUSTOM_TEXT_MODE_SLOT,
    DEFAULT_DASHBOARD_TEMPLATE,
    DEFAULT_DELIVERY_MODE,
    DEFAULT_ENABLED,
    DEFAULT_LOCALE,
    DEFAULT_ORDER,
    DEFAULT_PRIORITY,
    DEFAULT_RENDERING_STYLE,
    DOMAIN,
    SNIPPET_COMMON_SETTING_KEYS,
    SUBENTRY_TYPE_SNIPPET,
)
from .providers.registry import create_provider, ensure_builtin_providers_loaded, list_provider_metadata
from .subentries import get_config_subentry_data, get_config_subentry_options, iter_config_subentries


class UserBriefingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for User Briefing."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._profile: dict[str, Any] = {}
        self._defaults: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> UserBriefingOptionsFlow:
        """Return the options flow for this config entry."""
        return UserBriefingOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        config_entry: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported subentry flow handlers."""
        return {SUBENTRY_TYPE_SNIPPET: BriefingSnippetSubentryFlow}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect profile identity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            identity = user_input.get("identity", {})
            presentation = user_input.get("presentation", {})
            user_key = str(identity[CONF_USER_KEY]).strip().lower()

            await self.async_set_unique_id(user_key)
            self._abort_if_unique_id_configured()

            self._profile = {
                CONF_USER_KEY: user_key,
                CONF_DISPLAY_NAME: str(identity[CONF_DISPLAY_NAME]).strip(),
                CONF_LOCALE: presentation[CONF_LOCALE],
            }
            self.context["title_placeholders"] = {
                "name": self._profile[CONF_DISPLAY_NAME],
            }
            return await self.async_step_defaults()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("identity"): section(
                        vol.Schema(
                            {
                                vol.Required(CONF_DISPLAY_NAME): selector.TextSelector(),
                                vol.Required(CONF_USER_KEY): selector.TextSelector(),
                            }
                        ),
                        {"collapsed": False},
                    ),
                    vol.Required("presentation"): section(
                        vol.Schema(
                            {
                                vol.Required(CONF_LOCALE, default=DEFAULT_LOCALE): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=["en", "ca", "es"],
                                        translation_key="locale",
                                        mode=selector.SelectSelectorMode.DROPDOWN,
                                    )
                                )
                            }
                        ),
                        {"collapsed": False},
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_defaults(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect profile defaults."""
        if user_input is not None:
            self._defaults = {
                CONF_DASHBOARD_TEMPLATE: user_input[CONF_DASHBOARD_TEMPLATE],
                CONF_DASHBOARD_PATH: user_input.get(CONF_DASHBOARD_PATH),
                CONF_DEFAULT_DELIVERY_MODE: user_input[CONF_DEFAULT_DELIVERY_MODE],
                CONF_RENDERING_STYLE: user_input[CONF_RENDERING_STYLE],
            }
            return self.async_create_entry(
                title=self._profile[CONF_DISPLAY_NAME],
                data=self._profile,
                options=self._defaults,
            )

        return self.async_show_form(
            step_id="defaults",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DASHBOARD_TEMPLATE,
                        default=DEFAULT_DASHBOARD_TEMPLATE,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["default", "compact", "expanded"],
                            translation_key="dashboard_template",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(CONF_DASHBOARD_PATH): selector.TextSelector(),
                    vol.Required(
                        CONF_DEFAULT_DELIVERY_MODE,
                        default=DEFAULT_DELIVERY_MODE,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["dashboard", "notification_stub", "voice_future"],
                            translation_key="delivery_mode",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_RENDERING_STYLE,
                        default=DEFAULT_RENDERING_STYLE,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["friendly", "concise", "cheerful"],
                            translation_key="rendering_style",
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={"name": self._profile.get(CONF_DISPLAY_NAME, "")},
        )

    async def async_on_create_entry(self, result: FlowResult) -> FlowResult:
        """Continue to the first snippet flow after creating the profile."""
        subentry_result = await self.hass.config_entries.subentries.async_init(
            (result["result"].entry_id, SUBENTRY_TYPE_SNIPPET),
            context=config_entries.SubentryFlowContext(source=config_entries.SOURCE_USER),
        )
        result["next_flow"] = (
            config_entries.FlowType.CONFIG_SUBENTRIES_FLOW,
            subentry_result["flow_id"],
        )
        return result

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Update stable profile data."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                data_updates={
                    CONF_DISPLAY_NAME: user_input[CONF_DISPLAY_NAME],
                    CONF_LOCALE: user_input[CONF_LOCALE],
                },
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_DISPLAY_NAME): selector.TextSelector(),
                        vol.Required(CONF_LOCALE): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=["en", "ca", "es"],
                                translation_key="locale",
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                entry.data,
            ),
        )


class UserBriefingOptionsFlow(OptionsFlowWithReload):
    """Mutable profile options flow."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(CONF_USER_KEY): selector.TextSelector(
                            selector.TextSelectorConfig(read_only=True)
                        ),
                        vol.Required(
                            CONF_DASHBOARD_TEMPLATE,
                            default=DEFAULT_DASHBOARD_TEMPLATE,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=["default", "compact", "expanded"],
                                translation_key="dashboard_template",
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Optional(CONF_DASHBOARD_PATH): selector.TextSelector(),
                        vol.Required(
                            CONF_DEFAULT_DELIVERY_MODE,
                            default=DEFAULT_DELIVERY_MODE,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=["dashboard", "notification_stub", "voice_future"],
                                translation_key="delivery_mode",
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(
                            CONF_RENDERING_STYLE,
                            default=DEFAULT_RENDERING_STYLE,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=["friendly", "concise", "cheerful"],
                                translation_key="rendering_style",
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                {
                    CONF_USER_KEY: self.config_entry.data.get(CONF_USER_KEY),
                    **self.config_entry.options,
                },
            ),
        )


class BriefingSnippetSubentryFlow(ConfigSubentryFlow):
    """Handle user briefing snippet subentries."""

    def __init__(self) -> None:
        self._provider_key: str | None = None
        self._provider_config: dict[str, Any] = {}

    def _get_parent_entry(self) -> ConfigEntry:
        """Return the parent config entry for this subentry flow."""
        return self._get_entry()

    def _provider_instance(self):
        """Instantiate the current provider."""
        return create_provider(self.hass, self._provider_key)

    def _provider_config_from_subentry(self, config_subentry: object) -> dict[str, Any]:
        """Return provider-specific subentry data across HA storage variants."""
        return get_config_subentry_data(config_subentry, SNIPPET_COMMON_SETTING_KEYS)

    def _common_settings_from_user_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Return shared snippet settings from form input."""
        # CONF_TITLE_OVERRIDE is optional; all other keys are required.
        result = {
            k: user_input[k]
            for k in SNIPPET_COMMON_SETTING_KEYS
            if k != CONF_TITLE_OVERRIDE
        }
        result[CONF_TITLE_OVERRIDE] = user_input.get(CONF_TITLE_OVERRIDE)
        return result

    def _common_settings_from_subentry(self, config_subentry: object) -> dict[str, Any]:
        """Return shared snippet settings across HA storage variants."""
        return get_config_subentry_options(config_subentry, SNIPPET_COMMON_SETTING_KEYS)

    def _create_subentry_entry(
        self,
        title: str,
        provider_config: dict[str, Any],
        common_settings: dict[str, Any],
    ) -> FlowResult:
        """Create a snippet subentry across Home Assistant API variants."""
        data = {
            CONF_PROVIDER_KEY: self._provider_key,
            **provider_config,
        }
        try:
            return self.async_create_entry(
                title=title,
                data=data,
                options=common_settings,
            )
        except TypeError as err:
            if "unexpected keyword argument" not in str(err):
                raise
            return self.async_create_entry(
                title=title,
                data={
                    **data,
                    **common_settings,
                },
            )

    def _update_subentry_entry(
        self,
        config_subentry: object,
        title: str,
        provider_updates: dict[str, Any],
        common_settings: dict[str, Any],
    ) -> FlowResult:
        """Update a snippet subentry across Home Assistant API variants."""
        try:
            return self.async_update_and_abort(
                config_subentry,
                data_updates=provider_updates,
                options_updates=common_settings,
                title=title,
            )
        except TypeError as err:
            if "unexpected keyword argument" not in str(err):
                raise
            existing_provider_key = (getattr(config_subentry, "data", {}) or {}).get(CONF_PROVIDER_KEY)
            return self.async_update_and_abort(
                config_subentry,
                data_updates={
                    CONF_PROVIDER_KEY: existing_provider_key,
                    **provider_updates,
                    **common_settings,
                },
                title=title,
            )

    def _has_singleton_conflict(self, provider_key: str) -> bool:
        """Return whether a provider singleton already exists on the parent entry."""
        parent_entry = self._get_parent_entry()
        for subentry in iter_config_subentries(parent_entry, SUBENTRY_TYPE_SNIPPET):
            if subentry.data.get(CONF_PROVIDER_KEY) == provider_key:
                return True
        return False

    def _find_duplicate_subentry(
        self,
        provider_key: str,
        unique_key: str | None,
        ignore_subentry_id: str | None = None,
    ) -> bool:
        """Return whether a duplicate provider-source combination exists."""
        if not unique_key:
            return False

        parent_entry = self._get_parent_entry()
        provider = create_provider(self.hass, provider_key)
        for subentry in iter_config_subentries(parent_entry, SUBENTRY_TYPE_SNIPPET):
            if getattr(subentry, "subentry_id", None) == ignore_subentry_id:
                continue
            provider_config = self._provider_config_from_subentry(subentry)
            if provider_config.get(CONF_PROVIDER_KEY) != provider_key:
                continue
            existing_key = provider.get_instance_unique_key(provider_config)
            if existing_key == unique_key:
                return True
        return False

    def _build_common_schema(self) -> vol.Schema:
        """Return the shared snippet behavior schema."""
        return vol.Schema(
            {
                vol.Required(CONF_ENABLED, default=DEFAULT_ENABLED): bool,
                vol.Required(CONF_ORDER, default=DEFAULT_ORDER): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=999, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_PRIORITY, default=DEFAULT_PRIORITY): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["required", "optional"],
                        translation_key="snippet_priority",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_TITLE_OVERRIDE): selector.TextSelector(),
            }
        )

    def _get_subentry_title(
        self,
        provider,
        provider_config: dict[str, Any],
        title_override: str | None,
    ) -> str:
        """Return the stored title for a snippet subentry."""
        return title_override or provider.get_instance_title(provider_config)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select the provider type."""
        ensure_builtin_providers_loaded()

        if user_input is not None:
            provider_key = user_input[CONF_PROVIDER_KEY]
            self._provider_key = provider_key
            provider = self._provider_instance()
            if not provider.describe().supports_multiple_instances and self._has_singleton_conflict(provider_key):
                return self.async_abort(reason="provider_singleton")
            return await self.async_step_provider_config()

        provider_options = [
            selector.SelectOptionDict(value=metadata.key, label=metadata.name)
            for metadata in list_provider_metadata()
        ]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROVIDER_KEY): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=provider_options,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_provider_config(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure the provider-specific source."""
        provider = self._provider_instance()

        # custom_text has its own multi-step flow.
        if self._provider_key == "custom_text":
            if user_input is not None:
                self._provider_config = provider.validate_config(user_input)
                mode = user_input.get(CONF_CUSTOM_TEXT_MODE, CUSTOM_TEXT_MODE_SLOT)
                if mode == CUSTOM_TEXT_MODE_ENTITY:
                    return await self.async_step_custom_text_entity()
                return await self.async_step_custom_text_confirm()

            return self.async_show_form(
                step_id="provider_config",
                data_schema=provider.build_config_schema(),
            )

        if user_input is not None:
            self._provider_config = provider.validate_config(user_input)
            return await self.async_step_common()

        return self.async_show_form(
            step_id="provider_config",
            data_schema=provider.build_config_schema(),
        )

    async def async_step_custom_text_entity(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Choose entity source for custom_text entity-mode."""
        from .providers.custom_text import CustomTextProvider

        if user_input is not None:
            self._provider_config = CustomTextProvider(self.hass).validate_config(
                {**self._provider_config, **user_input}
            )
            return await self.async_step_common()

        return self.async_show_form(
            step_id="custom_text_entity",
            data_schema=CustomTextProvider(self.hass).build_entity_schema(),
        )

    async def async_step_custom_text_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Confirm slot creation and direct user to copy the ID after saving."""
        if user_input is not None:
            return await self.async_step_common()

        return self.async_show_form(
            step_id="custom_text_confirm",
            data_schema=vol.Schema({}),
        )

    async def async_step_common(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure common snippet behavior."""
        provider = self._provider_instance()
        provider_key = self._provider_key
        assert provider_key is not None
        if user_input is not None:
            instance_unique_key = provider.get_instance_unique_key(self._provider_config)
            if self._find_duplicate_subentry(provider_key, instance_unique_key):
                return self.async_abort(reason="duplicate_source")

            title = self._get_subentry_title(
                provider,
                self._provider_config,
                user_input.get(CONF_TITLE_OVERRIDE),
            )
            return self._create_subentry_entry(
                title,
                self._provider_config,
                self._common_settings_from_user_input(user_input),
            )

        return self.async_show_form(
            step_id="common",
            data_schema=self._build_common_schema(),
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Reconfigure an existing snippet subentry."""
        config_subentry = self._get_reconfigure_subentry()
        provider_config = self._provider_config_from_subentry(config_subentry)
        common_settings = self._common_settings_from_subentry(config_subentry)
        provider_key = provider_config[CONF_PROVIDER_KEY]
        provider = create_provider(self.hass, provider_key)

        if user_input is not None:
            provider_input = {
                key: value
                for key, value in user_input.items()
                if key not in SNIPPET_COMMON_SETTING_KEYS
            }
            provider_updates = provider.validate_reconfigure_config(provider_input)
            instance_unique_key = provider.get_instance_unique_key(provider_updates)
            if self._find_duplicate_subentry(
                provider_key,
                instance_unique_key,
                ignore_subentry_id=getattr(config_subentry, "subentry_id", None),
            ):
                return self.async_abort(reason="duplicate_source")

            title = self._get_subentry_title(
                provider,
                provider_updates,
                user_input.get(CONF_TITLE_OVERRIDE),
            )
            return self._update_subentry_entry(
                config_subentry,
                title,
                provider_updates,
                self._common_settings_from_user_input(user_input),
            )

        provider_schema = provider.build_reconfigure_schema(
            provider_config,
            common_settings,
        )
        suggested_values = {**provider_config, **common_settings}
        common_schema = self._build_common_schema()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    **provider_schema.schema,
                    **common_schema.schema,
                }),
                suggested_values,
            ),
        )