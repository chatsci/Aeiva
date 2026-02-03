"""
AEIVA Event System.

Provides the EventBus for pub/sub communication between neurons,
and EventNames for type-safe event name constants.
"""

from aeiva.event.event_bus import EventBus
from aeiva.event.event import Event
from aeiva.event.event_names import EventNames

__all__ = ["EventBus", "Event", "EventNames"]
