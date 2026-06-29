"""Home status provider scaffold."""

from homeassistant.helpers import selector

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class HomeStatusProvider(StubBriefingProvider):
    provider_key = "home_status"
    provider_name = "Home Status"
    supports_multiple_instances = False
    source_type = "entity"
    summary_limit_default = None

    def build_source_ref_selector(self):
        return selector.EntitySelector(selector.EntitySelectorConfig())