"""Beach conditions provider scaffold."""

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class BeachConditionsProvider(StubBriefingProvider):
    provider_key = "beach_conditions"
    provider_name = "Beach Conditions"