"""Compliment provider scaffold."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import voluptuous as vol

from ..models import SnippetResult
from .base_stub import StubBriefingProvider
from .registry import register_provider

_COMPLIMENTS = (
    "You are doing a great job keeping things moving.",
    "Your attention to detail is quietly making everything better.",
    "You have excellent taste in automations and integrations.",
    "You keep showing up and it really counts.",
)


@register_provider
class ComplimentProvider(StubBriefingProvider):
    provider_key = "compliment"
    provider_name = "Compliment"

    def build_config_schema(self) -> vol.Schema:
        return vol.Schema({})

    def validate_config(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def async_collect(self, config: dict[str, Any]) -> dict[str, Any]:
        index = datetime.now(UTC).timetuple().tm_yday % len(_COMPLIMENTS)
        return {"compliment": _COMPLIMENTS[index]}

    def normalize(self, payload: dict[str, Any], instance_id: str) -> SnippetResult:
        compliment = str(payload.get("compliment") or _COMPLIMENTS[0])
        return SnippetResult(
            provider_key=self.describe().key,
            instance_id=instance_id,
            status="ok",
            priority="optional",
            title=self.describe().name,
            text=compliment,
            scenario="compliment",
            data={"compliment": compliment},
        )