"""Structural expectations for config flow scaffold."""

from types import SimpleNamespace

from custom_components.user_briefing.config_flow import (
    BriefingSnippetSubentryFlow,
    UserBriefingConfigFlow,
    UserBriefingOptionsFlow,
)


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