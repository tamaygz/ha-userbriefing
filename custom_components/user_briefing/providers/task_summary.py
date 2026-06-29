"""Generic task-summary provider scaffold."""

from __future__ import annotations

from homeassistant.helpers import selector

from ..adapters.todo import TodoAdapter
from ..models import SnippetResult
from .base_stub import StubBriefingProvider
from .contracts import ProviderAdapter
from .registry import register_provider


def _extract_response_section(payload: dict, source_ref: str | None) -> dict:
    response = payload.get("response")
    if isinstance(response, dict):
        source_payload = response.get(source_ref) if source_ref else None
        if isinstance(source_payload, dict):
            return source_payload
        return response
    return {}


@register_provider
class TaskSummaryProvider(StubBriefingProvider):
    provider_key = "task_summary"
    provider_name = "Task Summary"
    source_type = "todo_entity"
    summary_limit_default = 5

    def build_source_ref_selector(self):
        return selector.EntitySelector(selector.EntitySelectorConfig(domain="todo"))

    def get_adapter(self) -> ProviderAdapter:
        return TodoAdapter(self.hass)

    def normalize(self, payload: dict[str, object], instance_id: str) -> SnippetResult:
        source_ref = payload.get("source_ref")
        response_section = _extract_response_section(payload, source_ref if isinstance(source_ref, str) else None)
        raw_items = response_section.get("items", []) if isinstance(response_section, dict) else []
        items = raw_items if isinstance(raw_items, list) else []
        open_items = [item for item in items if item.get("status") != "completed"]
        summary_limit = int(payload.get("summary_limit", 5))
        visible_items = open_items[:summary_limit]

        if not payload.get("available"):
            return SnippetResult(
                provider_key=self.describe().key,
                instance_id=instance_id,
                status="error",
                priority="optional",
                title=self.describe().name,
                text="Task data is unavailable right now.",
                scenario="error",
                data={"items": []},
                meta={"source_ref": source_ref},
            )

        if not visible_items:
            return SnippetResult(
                provider_key=self.describe().key,
                instance_id=instance_id,
                status="empty",
                priority="optional",
                title=self.describe().name,
                text="You have no open tasks right now.",
                scenario="empty",
                data={"items": open_items},
                meta={"source_ref": source_ref},
            )

        summaries = [str(item.get("summary") or "Untitled task") for item in visible_items]
        extra_count = max(0, len(open_items) - len(visible_items))
        extra_suffix = f" and {extra_count} more" if extra_count else ""
        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="ok",
            priority="optional",
            title=self.describe().name,
            text=f"Open tasks: {'; '.join(summaries)}{extra_suffix}.",
            scenario="tasks_ready",
            data={"items": open_items},
            meta={"source_ref": source_ref},
        )