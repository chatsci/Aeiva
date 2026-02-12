from __future__ import annotations

from asyncio import Future
from dataclasses import dataclass
from typing import Dict


@dataclass
class AckWaiter:
    expected: int
    future: Future[None]


@dataclass
class AckState:
    count: int
    seen_at: float


class AckTracker:
    """State container for command ACK accounting and waiter coordination."""

    def __init__(self, *, ttl_seconds: float, max_entries: int) -> None:
        self.ttl_seconds = float(ttl_seconds)
        self.max_entries = int(max_entries)
        self.states: Dict[str, AckState] = {}
        self.waiters: Dict[str, AckWaiter] = {}

    @staticmethod
    def new_state(*, count: int, seen_at: float) -> AckState:
        return AckState(count=max(0, int(count)), seen_at=float(seen_at))

    def count(self, command_id: str) -> int:
        state = self.states.get(command_id)
        return int(state.count) if state else 0

    def prune(self, *, now: float) -> None:
        if not self.states:
            return
        tick = float(now)
        stale_ids = [
            command_id
            for command_id, state in self.states.items()
            if (tick - float(state.seen_at)) > self.ttl_seconds
        ]
        for command_id in stale_ids:
            self.states.pop(command_id, None)

        overflow = len(self.states) - self.max_entries
        if overflow <= 0:
            return
        ordered = sorted(
            self.states.items(),
            key=lambda item: float(item[1].seen_at),
        )
        for command_id, _ in ordered[:overflow]:
            self.states.pop(command_id, None)

    def record(self, command_id: str, *, now: float) -> int:
        if not command_id:
            return 0
        state = self.states.get(command_id)
        if state is None:
            state = self.new_state(count=1, seen_at=now)
        else:
            state = self.new_state(count=state.count + 1, seen_at=now)
        self.states[command_id] = state
        self.prune(now=now)
        waiter = self.waiters.get(command_id)
        if waiter and state.count >= waiter.expected and not waiter.future.done():
            waiter.future.set_result(None)
        return state.count

    def clear(self) -> None:
        self.states.clear()
        self.waiters.clear()
