# event.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Event:
    """
    Represents an event in the event bus system.

    Attributes:
        name (str): The name of the event.
        payload (Any): The data associated with the event.
        timestamp (datetime): The time the event was created.
        priority (int): The priority of the event.
    """
    name: str
    payload: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0