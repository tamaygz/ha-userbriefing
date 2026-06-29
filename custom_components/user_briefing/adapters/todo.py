"""Task and to-do adapter.

Consumes existing Home Assistant task ecosystems (Local to-do, Todoist,
Microsoft To Do, and others) through the shared ``todo`` building block via the
``todo.get_items`` service response.
"""

from .base import HomeAssistantServiceAdapter


class TodoAdapter(HomeAssistantServiceAdapter):
    """Adapter for Home Assistant task-backed sources (``todo.get_items``)."""