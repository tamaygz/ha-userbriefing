"""Compliment provider scaffold."""

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class ComplimentProvider(StubBriefingProvider):
    provider_key = "compliment"
    provider_name = "Compliment"