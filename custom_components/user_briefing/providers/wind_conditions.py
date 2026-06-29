"""Wind conditions provider scaffold."""

from homeassistant.helpers import selector

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class WindConditionsProvider(StubBriefingProvider):
    provider_key = "wind_conditions"
    provider_name = "Wind Conditions"
    source_type = "entity"
    summary_limit_default = None

    def build_source_ref_selector(self):
        return selector.EntitySelector(selector.EntitySelectorConfig())