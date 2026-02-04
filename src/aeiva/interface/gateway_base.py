import asyncio
import logging
import queue
from collections import OrderedDict, deque
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Generic, List, Optional, Set, TypeVar

from aeiva.neuron import Signal
from aeiva.event.event_names import EventNames

logger = logging.getLogger(__name__)

RouteT = TypeVar("RouteT")


@dataclass
class PendingResponse(Generic[RouteT]):
    future: asyncio.Future
    trace_ids: Set[str] = field(default_factory=set)
    chunks: List[str] = field(default_factory=list)
    route: Optional[RouteT] = None


class GatewayBase(Generic[RouteT]):
    """
    Base gateway for event-driven interfaces.

    Responsibilities:
    - Track route by trace_id
    - Chain routes through perception.output
    - Resolve cognition.thought to route
    - Optional request/response for synchronous callers
    - Streaming: buffer or passthrough (configurable)
    """

    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Any,
        *,
        stream_mode: str = "buffer",
        response_timeout: float = 60.0,
        max_routes: int = 2048,
        pending_queue_max: int = 256,
    ) -> None:
        self.config = config or {}
        self.events = event_bus
        self.stream_mode = stream_mode
        self.response_timeout = response_timeout
        self.deliver_final_on_pass = True
        self.session_scope = (self.config.get("session_scope") or "shared").lower()
        self.channel_id = self.config.get("channel_id") or ""
        self.memory_user_id = self.config.get("memory_user_id") or self.config.get("user_id") or "User"

        self._routes: "OrderedDict[str, RouteT]" = OrderedDict()
        self._routes_lock = asyncio.Lock()
        self._max_routes = max_routes

        self._pending_routes: Deque[RouteT] = deque(maxlen=pending_queue_max)
        self._pending_routes_lock = asyncio.Lock()

        self._pending: Dict[str, PendingResponse[RouteT]] = {}
        self._pending_lock = asyncio.Lock()

        self._stream_buffers: Dict[str, List[str]] = {}
        self._stream_lock = asyncio.Lock()
        self._stream_routes: Dict[str, RouteT] = {}

    def register_handlers(self) -> None:
        if not self.events:
            return
        self.events.subscribe(EventNames.PERCEPTION_OUTPUT, self._handle_perception_output)
        self.events.subscribe(EventNames.COGNITION_THOUGHT, self._handle_cognition_event)
        self.events.subscribe(EventNames.AGENT_STOP, self._handle_agent_stop)

    def request_stop(self) -> None:
        return None

    async def emit_input(
        self,
        signal: Signal,
        *,
        route: Optional[RouteT] = None,
        event_name: str = EventNames.PERCEPTION_STIMULI,
        add_pending_route: bool = False,
        await_response: bool = False,
    ) -> Optional[str]:
        pending: Optional[PendingResponse[RouteT]] = None
        if route is not None:
            await self._remember_route(signal.trace_id, route)
            if add_pending_route:
                async with self._pending_routes_lock:
                    self._pending_routes.append(route)
        if await_response:
            pending = PendingResponse(future=asyncio.get_running_loop().create_future(), route=route)
            pending.trace_ids.add(signal.trace_id)
            async with self._pending_lock:
                self._pending[signal.trace_id] = pending

        if self.events:
            await self.events.emit(event_name, payload=signal)

        if not pending:
            return None
        try:
            return await asyncio.wait_for(pending.future, timeout=self.response_timeout)
        except asyncio.TimeoutError:
            await self._clear_pending(pending)
            raise

    def build_input_signal(
        self,
        payload: Any,
        *,
        source: str,
        route: Optional[RouteT] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        meta_payload = dict(meta or {})
        user_id = self._resolve_session_user_id(route)
        if user_id:
            meta_payload.setdefault("user_id", user_id)

        if meta_payload:
            data = {"data": payload, "meta": meta_payload}
        else:
            data = payload
        return Signal(source=source, data=data)

    async def _handle_perception_output(self, event: Any) -> None:
        payload = event.payload
        if not isinstance(payload, Signal):
            return
        parent_id = payload.parent_id
        if not parent_id:
            return
        route = await self._get_route(parent_id, pop=False)
        if route is not None:
            await self._remember_route(payload.trace_id, route)

        pending = await self._get_pending(parent_id)
        if pending:
            async with self._pending_lock:
                pending.trace_ids.add(payload.trace_id)
                self._pending[payload.trace_id] = pending

    async def _handle_cognition_event(self, event: Any) -> None:
        payload = event.payload
        signal = payload if isinstance(payload, Signal) else None
        data = payload.data if isinstance(payload, Signal) else payload
        if not isinstance(data, dict):
            data = {"text": str(data)}

        trace_key = self._extract_trace_key(signal, data)
        pending = await self._get_pending(trace_key) if trace_key else None
        route = await self._resolve_route(trace_key, data, payload)

        if data.get("streaming"):
            await self._handle_streaming(data, trace_key, pending, route)
            return

        text = self._extract_text(data)
        if text is None:
            return
        await self._deliver_response(text, trace_key, pending, route)

    async def _handle_streaming(
        self,
        data: Dict[str, Any],
        trace_key: Optional[str],
        pending: Optional[PendingResponse[RouteT]],
        route: Optional[RouteT],
    ) -> None:
        is_final = bool(data.get("final", False))
        chunk = data.get("thought") or ""
        if trace_key:
            async with self._stream_lock:
                if route is not None:
                    self._stream_routes[trace_key] = route
                elif trace_key in self._stream_routes:
                    route = self._stream_routes[trace_key]
                if is_final:
                    self._stream_routes.pop(trace_key, None)

        if self.stream_mode in ("pass", "both"):
            await self.on_stream_chunk(route, chunk, is_final)
            if is_final:
                await self.on_stream_end(route)

        if self.stream_mode in ("buffer", "both"):
            if not trace_key:
                return
            async with self._stream_lock:
                buffer = self._stream_buffers.setdefault(trace_key, [])
                if chunk:
                    buffer.append(chunk)
                if not is_final:
                    return
                full_text = data.get("full_thought")
                if not full_text:
                    full_text = "".join(buffer)
                self._stream_buffers.pop(trace_key, None)
            await self._deliver_response(full_text, trace_key, pending, route)
            return

        if is_final and self.stream_mode == "pass" and self.deliver_final_on_pass:
            full_text = data.get("full_thought") or ""
            await self._deliver_response(full_text, trace_key, pending, route)

    async def _deliver_response(
        self,
        text: str,
        trace_key: Optional[str],
        pending: Optional[PendingResponse[RouteT]],
        route: Optional[RouteT],
    ) -> None:
        if pending:
            await self._resolve_pending(pending, text)
            return
        if route is None and self.requires_route():
            return
        await self.send_message(route, text)

    async def send_message(self, route: Optional[RouteT], text: str) -> None:
        return None

    async def on_stream_chunk(self, route: Optional[RouteT], chunk: str, final: bool) -> None:
        return None

    async def on_stream_end(self, route: Optional[RouteT]) -> None:
        return None

    def requires_route(self) -> bool:
        return True

    async def _resolve_route(
        self,
        trace_key: Optional[str],
        data: Dict[str, Any],
        payload: Any,
    ) -> Optional[RouteT]:
        if trace_key:
            pop_route = not bool(data.get("route_keep"))
            route = await self._get_route(trace_key, pop=pop_route)
            if route is not None:
                return route

        source = self._extract_source(payload, data)
        if self.matches_source(source):
            async with self._pending_routes_lock:
                if self._pending_routes:
                    return self._pending_routes.popleft()
        return None

    def matches_source(self, source: str) -> bool:
        return False

    def route_user_id(self, route: Optional[RouteT]) -> Optional[str]:
        return None

    @staticmethod
    def _extract_source(payload: Any, data: Dict[str, Any]) -> str:
        if isinstance(payload, Signal):
            source = payload.source or ""
            if isinstance(payload.data, dict):
                return payload.data.get("source", source) or source
            return source
        return data.get("source", "")

    @staticmethod
    def _extract_trace_key(signal: Optional[Signal], data: Dict[str, Any]) -> Optional[str]:
        origin = data.get("origin_trace_id")
        if origin:
            return origin
        if signal and signal.parent_id:
            return signal.parent_id
        return None

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> Optional[str]:
        for key in ("thought", "output", "text", "full_thought"):
            if key in data and isinstance(data[key], str):
                return data[key]
        return None

    def _resolve_session_user_id(self, route: Optional[RouteT]) -> str:
        base = str(self.memory_user_id or "User")
        scope = (self.session_scope or "shared").lower()
        channel = (self.channel_id or "").strip()
        route_user = (self.route_user_id(route) or "").strip()

        if scope == "per_channel":
            return f"{base}@{channel}" if channel else base
        if scope == "per_user":
            return f"{base}@{route_user}" if route_user else base
        if scope == "per_channel_user":
            if channel and route_user:
                return f"{base}@{channel}:{route_user}"
            if channel:
                return f"{base}@{channel}"
            if route_user:
                return f"{base}@{route_user}"
            return base
        return base

    async def _remember_route(self, trace_id: str, route: RouteT) -> None:
        async with self._routes_lock:
            self._routes[trace_id] = route
            while len(self._routes) > self._max_routes:
                self._routes.popitem(last=False)

    async def _get_route(self, trace_id: Optional[str], *, pop: bool = False) -> Optional[RouteT]:
        if not trace_id:
            return None
        async with self._routes_lock:
            if pop:
                return self._routes.pop(trace_id, None)
            return self._routes.get(trace_id)

    async def _get_pending(self, trace_id: Optional[str]) -> Optional[PendingResponse[RouteT]]:
        if not trace_id:
            return None
        async with self._pending_lock:
            return self._pending.get(trace_id)

    async def _resolve_pending(self, pending: PendingResponse[RouteT], text: str) -> None:
        await self._clear_pending(pending)
        if not pending.future.done():
            pending.future.set_result(text)

    async def _clear_pending(self, pending: PendingResponse[RouteT]) -> None:
        async with self._pending_lock:
            for trace_id in list(pending.trace_ids):
                self._pending.pop(trace_id, None)

    async def _handle_agent_stop(self, event: Any) -> None:
        return None


class ResponseQueueGateway(GatewayBase[None]):
    def __init__(
        self,
        config: Dict[str, Any],
        event_bus: Any,
        response_queue: Any,
        *,
        stream_end_marker: str = "<END_OF_RESPONSE>",
        response_timeout: float = 60.0,
        require_route: bool = False,
    ) -> None:
        super().__init__(
            config,
            event_bus,
            stream_mode="pass",
            response_timeout=response_timeout,
            max_routes=int((config or {}).get("max_route_cache", 2048)),
            pending_queue_max=int((config or {}).get("max_pending_routes", 256)),
        )
        self._queue = response_queue
        self._stream_end_marker = stream_end_marker
        self.deliver_final_on_pass = False
        self._require_route = require_route
        self._trace_buffers: Dict[str, Deque[Any]] = {}
        self._trace_lock = threading.Lock()

    def requires_route(self) -> bool:
        return self._require_route

    async def _handle_cognition_event(self, event: Any) -> None:
        payload = event.payload
        signal = payload if isinstance(payload, Signal) else None
        data = payload.data if isinstance(payload, Signal) else payload
        if not isinstance(data, dict):
            data = {"text": str(data)}

        trace_key = self._extract_trace_key(signal, data)
        route = await self._resolve_route(trace_key, data, payload)
        if self._require_route and route is None:
            return

        if data.get("streaming"):
            chunk = data.get("thought") or ""
            if chunk:
                self._queue.put_nowait((trace_key, chunk))
            if data.get("final"):
                self._queue.put_nowait((trace_key, self._stream_end_marker))
            return

        text = self._extract_text(data)
        if text is None:
            return
        self._queue.put_nowait((trace_key, text))

    async def send_message(self, route: Optional[None], text: str) -> None:
        if self._require_route and route is None:
            return
        if text:
            self._queue.put_nowait(text)

    async def on_stream_chunk(self, route: Optional[None], chunk: str, final: bool) -> None:
        if self._require_route and route is None:
            return
        if chunk:
            self._queue.put_nowait(chunk)

    async def on_stream_end(self, route: Optional[None]) -> None:
        if self._require_route and route is None:
            return
        self._queue.put_nowait(self._stream_end_marker)

    def get_for_trace(self, trace_id: Optional[str], timeout: float) -> Any:
        if not trace_id:
            return self._queue.get(timeout=timeout)
        end = time.time() + timeout
        while True:
            with self._trace_lock:
                buffer = self._trace_buffers.get(trace_id)
                if buffer:
                    return buffer.popleft()
            remaining = end - time.time()
            if remaining <= 0:
                raise queue.Empty()
            item = self._queue.get(timeout=remaining)
            if isinstance(item, tuple) and len(item) == 2:
                item_trace, payload = item
            else:
                item_trace, payload = None, item
            if item_trace == trace_id:
                return payload
            if item_trace is None:
                return payload
            with self._trace_lock:
                self._trace_buffers.setdefault(item_trace, deque()).append(payload)
