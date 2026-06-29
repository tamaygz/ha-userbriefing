"""Wind conditions provider scaffold."""

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class WindConditionsProvider(StubBriefingProvider):
    provider_key = "wind_conditions"
    provider_name = "Wind Conditions"