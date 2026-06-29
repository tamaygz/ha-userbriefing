"""Catalunya Beaches adapter.

Consumes the existing ``ha-catalunya-beaches`` HACS integration by reading its
beach entities' state and attributes.
"""

from .base import HomeAssistantEntityAdapter


class CatalunyaBeachesAdapter(HomeAssistantEntityAdapter):
    """Adapter for Catalunya Beaches backed snippets (entity state)."""