import asyncio
import concurrent.futures
import logging
import sys
import threading
import time
from typing import Any, Dict, Optional

from aeiva.interface.gateway_base import GatewayBase
from aeiva.interface.progress_hints import build_progress_hint, normalize_progress_phases
from aeiva.neuron import Signal
from aeiva.event.event_names import EventNames

logger = logging.getLogger(__name__)


class TerminalGateway(GatewayBase[str]):
    """
    Terminal gateway that reads stdin and prints replies in the same terminal.

    - Inbound: user input -> perception.stimuli (Signal source=perception.terminal)
    - Outbound: cognition.thought -> terminal output
    """

    def __init__(self, config: Dict[str, Any], event_bus: Any) -> None:
        cfg = config or {}
        super().__init__(
            cfg,
            event_bus,
            stream_mode=str(cfg.get("stream_mode", "buffer")),
            response_timeout=float(cfg.get("response_timeout", 180.0)),
            max_routes=int(cfg.get("max_route_cache", 2048)),
            pending_queue_max=int(cfg.get("max_pending_routes", 256)),
        )
        self.prompt = str(cfg.get("prompt", "You: "))
        self._route_token = "terminal"
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = asyncio.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._streaming = False
        self._awaiting_sync_response = False
        self._hint_line_visible = False
        self._show_emotion = bool(cfg.get("show_emotion", False))
        self.response_label = str(cfg.get("response_label", "Response: "))
        self.progress_hint_enabled = bool(cfg.get("progress_hint_enabled", True))
        self.progress_hint_interval = max(
            0.1,
            float(cfg.get("progress_hint_interval", 4.0)),
        )
        self.progress_poll_timeout = max(
            0.05,
            float(cfg.get("progress_poll_timeout", 0.5)),
        )
        self._progress_phases = normalize_progress_phases(cfg.get("progress_hint_phases"))
        self.progress_hint_style = str(cfg.get("progress_hint_style", "status")).strip().lower() or "status"
        self.progress_hint_persist_after = max(
            0.0,
            float(cfg.get("progress_hint_persist_after", 8.0)),
        )

    async def setup(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.register_handlers()
        if self.events:
            self.events.subscribe(EventNames.EMOTION_CHANGED, self._handle_emotion_event)

    async def run(self) -> None:
        if not self._thread:
            self._running = True
            self._thread = threading.Thread(target=self._input_loop, daemon=True)
            self._thread.start()
            logger.info("Terminal gateway started.")
        await self._stop_event.wait()

    async def stop(self) -> None:
        self._running = False
        self._stop_event.set()

    def request_stop(self) -> None:
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        else:
            self._stop_event.set()

    def matches_source(self, source: str) -> bool:
        return "terminal" in (source or "").lower()

    async def send_message(self, route: Optional[str], text: str) -> None:
        if not text:
            return
        self._render_response(text, show_prompt=not self._awaiting_sync_response)

    async def on_stream_chunk(self, route: Optional[str], chunk: str, final: bool) -> None:
        if not chunk:
            return
        if not self._streaming:
            self._clear_status_line()
            sys.stdout.write("\r\033[K")
            print(self.response_label, end="", flush=True)
            self._streaming = True
        print(chunk, end="", flush=True)
        if final:
            print("", flush=True)
            if not self._awaiting_sync_response:
                print(self.prompt, end="", flush=True)
            self._streaming = False

    async def on_stream_end(self, route: Optional[str]) -> None:
        if self._streaming:
            print("", flush=True)
            if not self._awaiting_sync_response:
                print(self.prompt, end="", flush=True)
            self._streaming = False

    async def _handle_agent_stop(self, event: Any) -> None:
        self.request_stop()

    async def _handle_emotion_event(self, event: Any) -> None:
        payload = event.payload
        if isinstance(payload, Signal):
            payload = payload.data
        if not isinstance(payload, dict):
            return
        if not (self._show_emotion or payload.get("show")):
            return
        label = payload.get("label")
        state = payload.get("state")
        expression = payload.get("expression")
        message = "[Emotion]"
        if label is not None:
            message += f" label={label}"
        if state is not None:
            message += f" state={state}"
        if expression is not None:
            message += f" expression={expression}"
        self._clear_status_line()
        sys.stdout.write("\r\033[K")
        print(message, flush=True)
        if not self._awaiting_sync_response:
            print(self.prompt, end="", flush=True)

    def _input_loop(self) -> None:
        loop = self._loop
        if loop is None:
            return
        while self._running and not self._stop_event.is_set():
            try:
                user_input = input(self.prompt)
            except EOFError:
                self._running = False
                break
            except KeyboardInterrupt:
                self._running = False
                asyncio.run_coroutine_threadsafe(self.events.emit(EventNames.AGENT_STOP), loop)
                break

            if not self._running:
                break

            command = user_input.strip().lower()
            if command in {"exit", "quit", "/exit", "/quit"}:
                self._running = False
                asyncio.run_coroutine_threadsafe(self.events.emit(EventNames.AGENT_STOP), loop)
                self.request_stop()
                break
            if command in {"/emotion", "/emotion-state"}:
                asyncio.run_coroutine_threadsafe(
                    self.events.emit(
                        EventNames.EMOTION_QUERY,
                        payload={"type": "state", "show": True, "origin": "terminal"},
                    ),
                    loop,
                )
                continue

            signal = self.build_input_signal(
                user_input,
                source=EventNames.PERCEPTION_TERMINAL,
                route=self._route_token,
            )
            response_future = asyncio.run_coroutine_threadsafe(
                self.emit_input(
                    signal,
                    route=self._route_token,
                    add_pending_route=True,
                    event_name=EventNames.PERCEPTION_STIMULI,
                    await_response=True,
                ),
                loop,
            )
            self._wait_for_response(response_future)

    def _build_progress_hint(self, *, elapsed_seconds: float, hint_index: int) -> str:
        return build_progress_hint(
            elapsed_seconds=elapsed_seconds,
            hint_index=hint_index,
            phases=self._progress_phases,
        )

    def _show_status_line(self, text: str) -> None:
        sys.stdout.write("\r\033[K")
        sys.stdout.write(str(text))
        sys.stdout.flush()
        self._hint_line_visible = True

    def _clear_status_line(self) -> None:
        if not self._hint_line_visible:
            return
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        self._hint_line_visible = False

    def _render_response(self, text: str, *, show_prompt: bool = True) -> None:
        self._clear_status_line()
        sys.stdout.write("\r\033[K")
        print(self.response_label, end="", flush=True)
        print(text, flush=True)
        if show_prompt:
            print(self.prompt, end="", flush=True)

    def _emit_progress_hint(self, hint: str, *, elapsed_seconds: float) -> None:
        if self.progress_hint_style in {"line", "log"}:
            self._clear_status_line()
            sys.stdout.write("\r\033[K")
            print(f"[AEIVA] {hint}", flush=True)
            return
        self._show_status_line(hint)

    def _wait_for_response(
        self,
        response_future: "concurrent.futures.Future[str]",
        *,
        now_fn=time.time,
    ) -> None:
        start_at = now_fn()
        deadline = start_at + max(0.1, float(self.response_timeout))
        next_hint_at = start_at
        hint_index = 0
        self._awaiting_sync_response = True
        try:
            while self._running and not self._stop_event.is_set():
                now = now_fn()
                remaining = deadline - now
                if remaining <= 0:
                    self._render_response(
                        "I'm sorry, I didn't receive a response in time.",
                        show_prompt=False,
                    )
                    return
                try:
                    response = response_future.result(
                        timeout=min(self.progress_poll_timeout, max(0.05, remaining))
                    )
                    self._clear_status_line()
                    if isinstance(response, str) and response.strip():
                        self._render_response(response, show_prompt=False)
                    return
                except concurrent.futures.TimeoutError:
                    # TimeoutError is overloaded: it can mean either
                    # "poll timed out" or "the coroutine completed with timeout".
                    if response_future.done():
                        self._render_response(
                            "I'm sorry, I didn't receive a response in time.",
                            show_prompt=False,
                        )
                        return
                    now = now_fn()
                    if now >= deadline:
                        self._render_response(
                            "I'm sorry, I didn't receive a response in time.",
                            show_prompt=False,
                        )
                        return
                    if not self.progress_hint_enabled:
                        continue
                    if now < next_hint_at:
                        continue
                    hint = self._build_progress_hint(
                        elapsed_seconds=now - start_at,
                        hint_index=hint_index,
                    )
                    hint_index += 1
                    next_hint_at = now + self.progress_hint_interval
                    self._emit_progress_hint(hint, elapsed_seconds=now - start_at)
                except Exception as exc:
                    self._render_response(f"Error: {exc}", show_prompt=False)
                    return
        finally:
            self._awaiting_sync_response = False
            self._clear_status_line()
            if not response_future.done():
                response_future.cancel()
