"""Structural expectations for config flow scaffold."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import voluptuous as vol

import homeassistant.config_entries as _ha_config_entries

from custom_components.user_briefing.config_flow import (
    BriefingSnippetSubentryFlow,
    UserBriefingConfigFlow,
    UserBriefingOptionsFlow,
)
from custom_components.user_briefing.const import SUBENTRY_TYPE_SNIPPET


def test_config_flow_classes_exist() -> None:
    assert UserBriefingConfigFlow.VERSION == 1
    assert UserBriefingConfigFlow.MINOR_VERSION == 1
    assert UserBriefingOptionsFlow is not None
    assert BriefingSnippetSubentryFlow is not None


def test_subentry_flow_create_entry_falls_back_when_options_are_unsupported() -> None:
    flow = BriefingSnippetSubentryFlow()
    flow._provider_key = "calendar"
    calls: list[dict[str, object]] = []

    def fake_async_create_entry(**kwargs):
        calls.append(kwargs)
        if "options" in kwargs:
            raise TypeError("ConfigSubentryFlow.async_create_entry() got an unexpected keyword argument 'options'")
        return kwargs

    flow.async_create_entry = fake_async_create_entry  # type: ignore[method-assign]

    result = flow._create_subentry_entry(
        "Calendar",
        {"source_ref": "calendar.work"},
        {"enabled": True, "order": 10, "priority": "optional", "title_override": None},
    )

    assert len(calls) == 2
    assert "options" in calls[0]
    assert result["data"] == {
        "provider_key": "calendar",
        "source_ref": "calendar.work",
        "enabled": True,
        "order": 10,
        "priority": "optional",
        "title_override": None,
    }


def test_subentry_flow_update_entry_falls_back_when_options_updates_are_unsupported() -> None:
    flow = BriefingSnippetSubentryFlow()
    calls: list[dict[str, object]] = []
    config_subentry = SimpleNamespace(
        subentry_id="snippet-1",
        data={"provider_key": "calendar", "source_ref": "calendar.work"},
    )

    def fake_async_update_and_abort(subentry, **kwargs):
        del subentry
        calls.append(kwargs)
        if "options_updates" in kwargs:
            raise TypeError("ConfigSubentryFlow.async_update_and_abort() got an unexpected keyword argument 'options_updates'")
        return kwargs

    flow.async_update_and_abort = fake_async_update_and_abort  # type: ignore[method-assign]

    result = flow._update_subentry_entry(
        config_subentry,
        "Calendar",
        {"provider_key": "calendar", "source_ref": "calendar.work"},
        {"enabled": True, "order": 10, "priority": "optional", "title_override": None},
    )

    assert len(calls) == 2
    assert "options_updates" in calls[0]
    assert result["data_updates"]["provider_key"] == "calendar"  # explicitly preserved
    assert result["data_updates"] == {
        "provider_key": "calendar",
        "source_ref": "calendar.work",
        "enabled": True,
        "order": 10,
        "priority": "optional",
        "title_override": None,
    }


def test_create_subentry_entry_stores_options_separately_when_supported() -> None:
    """Normal path: options stored separately, nothing merged into data."""
    flow = BriefingSnippetSubentryFlow()
    flow._provider_key = "calendar"
    calls: list[dict[str, object]] = []

    def accept_options(**kwargs):
        calls.append(kwargs)
        return kwargs

    flow.async_create_entry = accept_options  # type: ignore[method-assign]

    result = flow._create_subentry_entry(
        "Calendar",
        {"source_ref": "calendar.work"},
        {"enabled": True, "order": 10, "priority": "optional", "title_override": None},
    )

    assert len(calls) == 1  # no fallback triggered
    assert calls[0]["options"] == {
        "enabled": True, "order": 10, "priority": "optional", "title_override": None,
    }
    assert "enabled" not in result["data"]  # common settings NOT merged into data


def test_create_subentry_entry_reraises_unrelated_type_error() -> None:
    import pytest

    flow = BriefingSnippetSubentryFlow()
    flow._provider_key = "calendar"

    def always_raise(**kwargs):
        raise TypeError("unexpected keyword argument 'title_template'")

    flow.async_create_entry = always_raise  # type: ignore[method-assign]

    with pytest.raises(TypeError, match="title_template"):
        flow._create_subentry_entry(
            "Calendar",
            {"source_ref": "calendar.work"},
            {"enabled": True, "order": 10, "priority": "optional", "title_override": None},
        )


def test_update_subentry_entry_reraises_unrelated_type_error() -> None:
    import pytest

    flow = BriefingSnippetSubentryFlow()
    subentry = SimpleNamespace(subentry_id="snippet-1", data={})

    def always_raise(sub, **kwargs):
        raise TypeError("unexpected keyword argument 'title_template'")

    flow.async_update_and_abort = always_raise  # type: ignore[method-assign]

    with pytest.raises(TypeError, match="title_template"):
        flow._update_subentry_entry(
            subentry,
            "Calendar",
            {"provider_key": "calendar", "source_ref": "calendar.work"},
            {"enabled": True, "order": 10, "priority": "optional", "title_override": None},
        )

# ===========================================================================
# Singleton provider prevention
# ===========================================================================


def test_has_singleton_conflict_returns_false_when_no_subentries() -> None:
    """No subentries means no singleton conflict."""
    flow = BriefingSnippetSubentryFlow()
    parent_entry = SimpleNamespace(subentries={})
    flow._get_parent_entry = lambda: parent_entry  # type: ignore[method-assign]
    assert flow._has_singleton_conflict("home_status") is False


def test_has_singleton_conflict_returns_false_when_different_provider_key() -> None:
    """An existing subentry with a different provider key is not a conflict."""
    flow = BriefingSnippetSubentryFlow()
    subentry = SimpleNamespace(
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        data={"provider_key": "calendar"},
    )
    parent_entry = SimpleNamespace(subentries={"s1": subentry})
    flow._get_parent_entry = lambda: parent_entry  # type: ignore[method-assign]
    assert flow._has_singleton_conflict("home_status") is False


def test_has_singleton_conflict_returns_true_when_provider_already_added() -> None:
    """Existing subentry with the same provider key triggers a singleton conflict."""
    flow = BriefingSnippetSubentryFlow()
    subentry = SimpleNamespace(
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        data={"provider_key": "home_status"},
    )
    parent_entry = SimpleNamespace(subentries={"s1": subentry})
    flow._get_parent_entry = lambda: parent_entry  # type: ignore[method-assign]
    assert flow._has_singleton_conflict("home_status") is True


# ===========================================================================
# Duplicate source prevention
# ===========================================================================


def test_find_duplicate_subentry_skips_check_when_unique_key_is_none() -> None:
    """No duplicate detection is possible without a unique key."""
    flow = BriefingSnippetSubentryFlow()
    assert flow._find_duplicate_subentry("calendar", None) is False


def test_find_duplicate_subentry_returns_false_when_source_not_seen_before() -> None:
    """No duplicate if no subentry shares the same provider+source combination."""
    flow = BriefingSnippetSubentryFlow()
    flow.hass = SimpleNamespace()  # type: ignore[assignment]
    subentry = SimpleNamespace(
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        subentry_id="s1",
        data={
            "provider_key": "weather_forecast",
            "source_ref": "weather.home",
            "source_type": "weather_entity",
        },
        options={},
    )
    parent_entry = SimpleNamespace(subentries={"s1": subentry})
    flow._get_parent_entry = lambda: parent_entry  # type: ignore[method-assign]
    # Looking for a calendar source; only a weather subentry exists
    assert flow._find_duplicate_subentry("calendar", "calendar_entity:calendar.work") is False


def test_find_duplicate_subentry_returns_true_when_same_provider_and_source_exists() -> None:
    """Duplicate detected when provider key and source reference already exist."""
    flow = BriefingSnippetSubentryFlow()
    flow.hass = SimpleNamespace()  # type: ignore[assignment]
    subentry = SimpleNamespace(
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        subentry_id="s1",
        data={
            "provider_key": "calendar",
            "source_ref": "calendar.work",
            "source_type": "calendar_entity",
        },
        options={},
    )
    parent_entry = SimpleNamespace(subentries={"s1": subentry})
    flow._get_parent_entry = lambda: parent_entry  # type: ignore[method-assign]
    assert flow._find_duplicate_subentry("calendar", "calendar_entity:calendar.work") is True


def test_find_duplicate_subentry_ignores_current_subentry_during_reconfigure() -> None:
    """The subentry being reconfigured must be excluded from duplicate detection."""
    flow = BriefingSnippetSubentryFlow()
    flow.hass = SimpleNamespace()  # type: ignore[assignment]
    subentry = SimpleNamespace(
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        subentry_id="s1",
        data={
            "provider_key": "calendar",
            "source_ref": "calendar.work",
            "source_type": "calendar_entity",
        },
        options={},
    )
    parent_entry = SimpleNamespace(subentries={"s1": subentry})
    flow._get_parent_entry = lambda: parent_entry  # type: ignore[method-assign]
    # Same unique key — but it belongs to the subentry currently being reconfigured
    assert (
        flow._find_duplicate_subentry(
            "calendar",
            "calendar_entity:calendar.work",
            ignore_subentry_id="s1",
        )
        is False
    )


# ===========================================================================
# Post-create subentry chaining
# ===========================================================================


def test_on_create_entry_starts_snippet_subentry_flow() -> None:
    """async_on_create_entry must launch a snippet subentry flow and set next_flow."""
    flow = UserBriefingConfigFlow()

    init_calls: list[dict] = []

    async def fake_async_init(key, context=None):
        init_calls.append({"key": key, "context": context})
        return {"flow_id": "stub-flow-id"}

    hass = SimpleNamespace()
    hass.config_entries = SimpleNamespace()  # type: ignore[assignment]
    hass.config_entries.subentries = SimpleNamespace()
    hass.config_entries.subentries.async_init = fake_async_init
    flow.hass = hass  # type: ignore[assignment]

    entry = SimpleNamespace(entry_id="entry-abc")
    result: dict = {"result": entry}

    fake_flow_type = SimpleNamespace(CONFIG_SUBENTRIES_FLOW="config_subentries_flow")
    with (
        patch.object(
            _ha_config_entries,
            "SubentryFlowContext",
            lambda source: SimpleNamespace(source=source),
            create=True,
        ),
        patch.object(_ha_config_entries, "FlowType", fake_flow_type, create=True),
    ):
        out = asyncio.run(flow.async_on_create_entry(result))

    assert len(init_calls) == 1
    assert init_calls[0]["key"][0] == "entry-abc"
    assert init_calls[0]["key"][1] == SUBENTRY_TYPE_SNIPPET
    assert "next_flow" in out
    assert out["next_flow"][1] == "stub-flow-id"


# ===========================================================================
# Provider-driven reconfigure
# ===========================================================================


def test_reconfigure_form_uses_provider_build_reconfigure_schema() -> None:
    """async_step_reconfigure must ask the provider for its reconfigure schema."""
    flow = BriefingSnippetSubentryFlow()
    flow.hass = SimpleNamespace()  # type: ignore[assignment]

    subentry = SimpleNamespace(
        subentry_id="s1",
        data={
            "provider_key": "calendar",
            "source_ref": "calendar.work",
            "source_type": "calendar_entity",
        },
        options={"enabled": True, "order": 10, "priority": "optional", "title_override": None},
    )
    flow._get_reconfigure_subentry = lambda: subentry  # type: ignore[method-assign]

    reconfigure_schema_calls: list[tuple] = []

    class _FakeProvider:
        def describe(self):
            return SimpleNamespace(key="calendar")

        def build_reconfigure_schema(self, existing_data, existing_options):
            reconfigure_schema_calls.append((dict(existing_data), dict(existing_options)))
            return vol.Schema({})

        def validate_reconfigure_config(self, user_input):
            return dict(user_input)

        def get_instance_unique_key(self, config):
            return config.get("source_ref")

    shown_forms: list[dict] = []
    flow.async_show_form = lambda **kwargs: shown_forms.append(kwargs) or kwargs  # type: ignore[method-assign]
    flow.add_suggested_values_to_schema = lambda schema, values: schema  # type: ignore[method-assign]

    with patch(
        "custom_components.user_briefing.config_flow.create_provider",
        return_value=_FakeProvider(),
    ):
        asyncio.run(flow.async_step_reconfigure(None))

    assert len(reconfigure_schema_calls) == 1
    existing_data, _ = reconfigure_schema_calls[0]
    assert existing_data["source_ref"] == "calendar.work"
    assert len(shown_forms) == 1
    assert shown_forms[0]["step_id"] == "reconfigure"


def test_reconfigure_submission_uses_validate_reconfigure_config() -> None:
    """async_step_reconfigure must validate via validate_reconfigure_config, not validate_config."""
    flow = BriefingSnippetSubentryFlow()
    flow.hass = SimpleNamespace()  # type: ignore[assignment]

    subentry = SimpleNamespace(
        subentry_id="s1",
        data={
            "provider_key": "calendar",
            "source_ref": "calendar.work",
            "source_type": "calendar_entity",
        },
        options={"enabled": True, "order": 10, "priority": "optional", "title_override": None},
    )
    flow._get_reconfigure_subentry = lambda: subentry  # type: ignore[method-assign]

    validate_reconfigure_calls: list[dict] = []

    class _FakeProvider:
        def describe(self):
            return SimpleNamespace(key="calendar")

        def validate_reconfigure_config(self, user_input):
            validate_reconfigure_calls.append(dict(user_input))
            return dict(user_input)

        def get_instance_unique_key(self, config):
            return None

        def get_instance_title(self, config):
            return "Calendar: new"

    update_calls: list = []
    flow._find_duplicate_subentry = lambda *a, **kw: False  # type: ignore[method-assign]
    flow._update_subentry_entry = lambda *a, **kw: update_calls.append(a) or {}  # type: ignore[method-assign]

    user_input = {
        "source_ref": "calendar.new",
        "enabled": True,
        "order": 10,
        "priority": "optional",
        "title_override": None,
    }

    with patch(
        "custom_components.user_briefing.config_flow.create_provider",
        return_value=_FakeProvider(),
    ):
        asyncio.run(flow.async_step_reconfigure(user_input))

    assert len(validate_reconfigure_calls) == 1
    # Common settings must be stripped; only provider-specific keys are validated
    assert "source_ref" in validate_reconfigure_calls[0]
    assert "enabled" not in validate_reconfigure_calls[0]
    assert len(update_calls) == 1


def test_reconfigure_aborts_when_new_source_is_a_duplicate() -> None:
    """async_step_reconfigure must abort when the new source already exists in another subentry."""
    flow = BriefingSnippetSubentryFlow()
    flow.hass = SimpleNamespace()  # type: ignore[assignment]

    subentry = SimpleNamespace(
        subentry_id="s1",
        data={
            "provider_key": "calendar",
            "source_ref": "calendar.work",
            "source_type": "calendar_entity",
        },
        options={"enabled": True, "order": 10, "priority": "optional", "title_override": None},
    )
    flow._get_reconfigure_subentry = lambda: subentry  # type: ignore[method-assign]

    class _FakeProvider:
        def describe(self):
            return SimpleNamespace(key="calendar")

        def validate_reconfigure_config(self, user_input):
            return dict(user_input)

        def get_instance_unique_key(self, config):
            src = config.get("source_ref")
            return f"calendar_entity:{src}" if src else None

    abort_calls: list[dict] = []
    flow.async_abort = lambda reason: abort_calls.append({"reason": reason}) or {"reason": reason}  # type: ignore[method-assign]

    # A second subentry already holds the source the user is trying to switch to
    existing_subentry = SimpleNamespace(
        subentry_type=SUBENTRY_TYPE_SNIPPET,
        subentry_id="s2",
        data={
            "provider_key": "calendar",
            "source_ref": "calendar.home",
            "source_type": "calendar_entity",
        },
        options={},
    )
    parent_entry = SimpleNamespace(subentries={"s2": existing_subentry})
    flow._get_parent_entry = lambda: parent_entry  # type: ignore[method-assign]

    user_input = {
        "source_ref": "calendar.home",
        "enabled": True,
        "order": 10,
        "priority": "optional",
        "title_override": None,
    }

    with patch(
        "custom_components.user_briefing.config_flow.create_provider",
        return_value=_FakeProvider(),
    ):
        result = asyncio.run(flow.async_step_reconfigure(user_input))

    assert result["reason"] == "duplicate_source"
    assert len(abort_calls) == 1
