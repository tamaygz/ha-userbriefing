"""Mail summary provider scaffold."""

from .base_stub import StubBriefingProvider
from .registry import register_provider


@register_provider
class MailSummaryStubProvider(StubBriefingProvider):
    provider_key = "mail_summary_stub"
    provider_name = "Mail Summary Stub"
    source_type = "integration"
    summary_limit_default = 5