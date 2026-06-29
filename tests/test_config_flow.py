"""Structural expectations for config flow scaffold."""

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