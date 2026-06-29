"""News provider scaffold."""

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class NewsHeadlinesProvider(StubBriefingProvider):
    provider_key = "news_headlines"
    provider_name = "News Headlines"