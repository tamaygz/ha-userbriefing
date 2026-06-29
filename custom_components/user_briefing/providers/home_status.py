"""Home status provider scaffold."""

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class HomeStatusProvider(StubBriefingProvider):
    provider_key = "home_status"
    provider_name = "Home Status"
    supports_multiple_instances = False