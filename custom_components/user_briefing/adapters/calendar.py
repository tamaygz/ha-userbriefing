"""Calendar adapter.

Consumes the existing Home Assistant ``calendar`` integration via the
``calendar.get_events`` service response.
"""

from .base import HomeAssistantServiceAdapter


class CalendarAdapter(HomeAssistantServiceAdapter):
    """Adapter for calendar-backed sources (``calendar.get_events``)."""