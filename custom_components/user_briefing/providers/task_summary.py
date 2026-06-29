"""Generic task-summary provider scaffold."""

import voluptuous as vol
from homeassistant.helpers import selector

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class TaskSummaryProvider(StubBriefingProvider):
    provider_key = "task_summary"
    provider_name = "Task Summary"

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required("source_type", default="todo_entity"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["todo_entity"],
                        translation_key="provider_source_type",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("source_ref"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="todo")
                ),
                vol.Optional("summary_limit", default=5): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=20, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )