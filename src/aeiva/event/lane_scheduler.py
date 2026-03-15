from __future__ import annotations

import asyncio
from collections import Counter, deque
from dataclasses import dataclass
import time
from typing import Any, Awaitable, Callable, Deque, Dict, Optional, Set, Tuple

from aeiva.event.event import Event
from aeiva.event.event_policy import EventPolicy


DispatchFn = Callable[[Event, Any], Awaitable[None]]
OnCompleteFn = Callable[[], None]


@dataclass
class _ScheduledEvent:
    event: Event
    only: Any
    enqueued_at: float
    policy: EventPolicy
    consistency_key: str
    on_complete: Optional[OnCompleteFn]


class LaneScheduler:
    """
    Partitioned scheduler:
    - mutating: per-key FIFO lane, one in-flight per lane
    - readonly: bounded parallel pool
    """

    def __init__(
        self,
        *,
        dispatch_fn: DispatchFn,
        lane_queue_limit: int = 2048,
        readonly_concurrency: int = 8,
        queue_wait_samples_max: int = 4096,
    ) -> None:
        self._dispatch_fn = dispatch_fn
        self._lane_queue_limit = max(1, int(lane_queue_limit))
        self._readonly_concurrency = max(1, int(readonly_concurrency))
        self._readonly_sem = asyncio.Semaphore(self._readonly_concurrency)
        self._queue_wait_samples: Deque[float] = deque(maxlen=max(128, int(queue_wait_samples_max)))

        self._lane_queues: Dict[str, Deque[_ScheduledEvent]] = {}
        self._lane_tasks: Dict[str, asyncio.Task] = {}
        self._readonly_tasks: Set[asyncio.Task] = set()

        self._queue_depth = 0
        self._drop_count = 0
        self._key_counter: Counter[str] = Counter()
        self._lock = asyncio.Lock()
        self._stopped = False

    async def submit(
        self,
        *,
        event: Event,
        only: Any,
        enqueued_at: float,
        policy: EventPolicy,
        consistency_key: str,
        on_complete: Optional[OnCompleteFn] = None,
    ) -> bool:
        if self._stopped:
            if on_complete:
                on_complete()
            return False

        scheduled = _ScheduledEvent(
            event=event,
            only=only,
            enqueued_at=float(enqueued_at),
            policy=policy,
            consistency_key=consistency_key or "global",
            on_complete=on_complete,
        )

        async with self._lock:
            self._key_counter[scheduled.consistency_key] += 1

            if self._is_readonly(policy):
                self._queue_depth += 1
                task = asyncio.create_task(self._run_readonly(scheduled))
                self._readonly_tasks.add(task)
                task.add_done_callback(self._readonly_tasks.discard)
                return True

            lane = self._lane_queues.setdefault(scheduled.consistency_key, deque())
            if len(lane) >= self._lane_queue_limit:
                self._drop_count += 1
                if scheduled.on_complete:
                    scheduled.on_complete()
                return False

            lane.append(scheduled)
            self._queue_depth += 1
            if scheduled.consistency_key not in self._lane_tasks:
                task = asyncio.create_task(self._run_lane(scheduled.consistency_key))
                self._lane_tasks[scheduled.consistency_key] = task
                task.add_done_callback(lambda _t, key=scheduled.consistency_key: self._lane_tasks.pop(key, None))
            return True

    def shutdown(self) -> None:
        self._stopped = True
        for task in list(self._lane_tasks.values()):
            task.cancel()
        for task in list(self._readonly_tasks):
            task.cancel()

    def snapshot_metrics(self, *, top_n: int = 10) -> Dict[str, Any]:
        wait_samples = list(self._queue_wait_samples)
        if wait_samples:
            sorted_wait = sorted(wait_samples)
            p95_idx = max(0, int(0.95 * (len(sorted_wait) - 1)))
            queue_wait = {
                "avg": round(sum(wait_samples) / len(wait_samples), 3),
                "p95": round(sorted_wait[p95_idx], 3),
                "samples": len(wait_samples),
            }
        else:
            queue_wait = {"avg": 0.0, "p95": 0.0, "samples": 0}

        return {
            "queue_depth": int(self._queue_depth),
            "queue_wait_ms": queue_wait,
            "drop_count": int(self._drop_count),
            "hot_key_topN": [
                {"key": key, "count": count}
                for key, count in self._key_counter.most_common(max(1, int(top_n)))
            ],
        }

    async def _run_readonly(self, scheduled: _ScheduledEvent) -> None:
        try:
            async with self._readonly_sem:
                await self._dispatch_scheduled(scheduled)
        finally:
            await self._mark_done()
            if scheduled.on_complete:
                scheduled.on_complete()

    async def _run_lane(self, consistency_key: str) -> None:
        while True:
            async with self._lock:
                lane = self._lane_queues.get(consistency_key)
                if not lane:
                    self._lane_queues.pop(consistency_key, None)
                    return
                scheduled = lane.popleft()

            try:
                await self._dispatch_scheduled(scheduled)
            finally:
                await self._mark_done()
                if scheduled.on_complete:
                    scheduled.on_complete()

    async def _dispatch_scheduled(self, scheduled: _ScheduledEvent) -> None:
        wait_ms = max(0.0, (time.monotonic() - scheduled.enqueued_at) * 1000.0)
        self._queue_wait_samples.append(wait_ms)
        await self._dispatch_fn(scheduled.event, scheduled.only)

    async def _mark_done(self) -> None:
        async with self._lock:
            if self._queue_depth > 0:
                self._queue_depth -= 1

    @staticmethod
    def _is_readonly(policy: EventPolicy) -> bool:
        return str(policy.mode or "").strip().lower() == "readonly"
