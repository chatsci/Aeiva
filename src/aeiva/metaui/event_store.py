from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Sequence

from .protocol import MetaUIEvent


@dataclass(frozen=True)
class EventStoreHealth:
    size: int
    capacity: int
    occupancy_ratio: float
    pressure_level: str
    dropped_events: int
    duplicate_event_ids: int
    accepted_event_ids: int
    queried_events: int
    consumed_events: int
    max_observed_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "size": self.size,
            "capacity": self.capacity,
            "occupancy_ratio": self.occupancy_ratio,
            "pressure_level": self.pressure_level,
            "dropped_events": self.dropped_events,
            "duplicate_event_ids": self.duplicate_event_ids,
            "accepted_event_ids": self.accepted_event_ids,
            "queried_events": self.queried_events,
            "consumed_events": self.consumed_events,
            "max_observed_size": self.max_observed_size,
        }


class MetaUIEventStore:
    def __init__(self, *, limit: int) -> None:
        maxlen = max(64, int(limit))
        self._events: Deque[MetaUIEvent] = deque(maxlen=maxlen)
        self._recent_ids: Deque[str] = deque(maxlen=maxlen)
        self._recent_id_set: set[str] = set()
        self._dropped_events = 0
        self._duplicate_event_ids = 0
        self._accepted_event_ids = 0
        self._queried_events = 0
        self._consumed_events = 0
        self._max_observed_size = 0

    @property
    def size(self) -> int:
        return len(self._events)

    @property
    def capacity(self) -> int:
        return int(self._events.maxlen or 0)

    def clear(self) -> None:
        self._events.clear()
        self._recent_ids.clear()
        self._recent_id_set.clear()
        self._dropped_events = 0
        self._duplicate_event_ids = 0
        self._accepted_event_ids = 0
        self._queried_events = 0
        self._consumed_events = 0
        self._max_observed_size = 0

    def accept_event_id(self, event_id: str) -> bool:
        if not event_id:
            return False
        if event_id in self._recent_id_set:
            self._duplicate_event_ids += 1
            return False
        if len(self._recent_ids) == self._recent_ids.maxlen:
            dropped = self._recent_ids[0]
            self._recent_id_set.discard(dropped)
        self._recent_ids.append(event_id)
        self._recent_id_set.add(event_id)
        self._accepted_event_ids += 1
        return True

    def append(self, event: MetaUIEvent) -> None:
        if len(self._events) == self.capacity and self.capacity > 0:
            self._dropped_events += 1
        self._events.append(event)
        self._max_observed_size = max(self._max_observed_size, len(self._events))

    def query(
        self,
        *,
        ui_id: Optional[str],
        session_id: Optional[str],
        event_types: Optional[Sequence[str]],
        since_ts: Optional[float],
        limit: int,
        consume: bool,
    ) -> tuple[list[MetaUIEvent], bool]:
        normalized_limit = max(1, min(int(limit), 500))
        type_set = {
            item
            for item in (event_types or [])
            if isinstance(item, str) and item.strip()
        }

        selected: list[MetaUIEvent] = []
        kept: Deque[MetaUIEvent] = deque(maxlen=self._events.maxlen)
        for event in self._events:
            if ui_id and event.ui_id != ui_id:
                kept.append(event)
                continue
            if session_id and event.session_id != session_id:
                kept.append(event)
                continue
            if since_ts is not None and event.ts <= since_ts:
                kept.append(event)
                continue
            if type_set and event.event_type not in type_set:
                kept.append(event)
                continue
            if len(selected) < normalized_limit:
                selected.append(event)
            else:
                kept.append(event)
        consumed = bool(consume and selected)
        if consumed:
            self._events = kept
            self._consumed_events += len(selected)
        self._queried_events += len(selected)
        return selected, consumed

    def health_snapshot(self) -> EventStoreHealth:
        capacity = self.capacity
        size = self.size
        occupancy_ratio = (size / float(capacity)) if capacity > 0 else 0.0
        if self._dropped_events > 0 or occupancy_ratio >= 0.9:
            pressure_level = "high"
        elif occupancy_ratio >= 0.7:
            pressure_level = "elevated"
        else:
            pressure_level = "normal"
        return EventStoreHealth(
            size=size,
            capacity=capacity,
            occupancy_ratio=occupancy_ratio,
            pressure_level=pressure_level,
            dropped_events=self._dropped_events,
            duplicate_event_ids=self._duplicate_event_ids,
            accepted_event_ids=self._accepted_event_ids,
            queried_events=self._queried_events,
            consumed_events=self._consumed_events,
            max_observed_size=self._max_observed_size,
        )
