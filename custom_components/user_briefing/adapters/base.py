"""Base adapter helpers."""

from __future__ import annotations

from typing import Any

from ..providers.contracts import ProviderAdapter


class StubAdapter(ProviderAdapter):
    """Simple adapter placeholder."""

    async def async_fetch(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"context": context, "items": []}