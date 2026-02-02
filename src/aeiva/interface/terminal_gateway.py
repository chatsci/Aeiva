import asyncio
import logging
import sys
import threading
from typing import Any, Dict, Optional

from aeiva.interface.gateway_base import GatewayBase

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
            response_timeout=float(cfg.get("response_timeout", 60.0)),
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

    async def setup(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.register_handlers()

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
        sys.stdout.write("\r\033[K")
        print("Response: ", end="", flush=True)
        print(text, flush=True)
        print(self.prompt, end="", flush=True)

    async def on_stream_chunk(self, route: Optional[str], chunk: str, final: bool) -> None:
        if not chunk:
            return
        if not self._streaming:
            sys.stdout.write("\r\033[K")
            print("Response: ", end="", flush=True)
            self._streaming = True
        print(chunk, end="", flush=True)
        if final:
            print("", flush=True)
            print(self.prompt, end="", flush=True)
            self._streaming = False

    async def on_stream_end(self, route: Optional[str]) -> None:
        if self._streaming:
            print("", flush=True)
            print(self.prompt, end="", flush=True)
            self._streaming = False

    async def _handle_agent_stop(self, event: Any) -> None:
        self.request_stop()

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
                asyncio.run_coroutine_threadsafe(self.events.emit("agent.stop"), loop)
                break

            if not self._running:
                break

            command = user_input.strip().lower()
            if command in {"exit", "quit", "/exit", "/quit"}:
                self._running = False
                asyncio.run_coroutine_threadsafe(self.events.emit("agent.stop"), loop)
                self.request_stop()
                break
            if command in {"/emotion", "/emotion-state"}:
                asyncio.run_coroutine_threadsafe(
                    self.events.emit(
                        "emotion.query",
                        payload={"type": "state", "show": True, "origin": "terminal"},
                    ),
                    loop,
                )
                continue

            signal = self.build_input_signal(
                user_input,
                source="perception.terminal",
                route=self._route_token,
            )
            asyncio.run_coroutine_threadsafe(
                self.emit_input(
                    signal,
                    route=self._route_token,
                    add_pending_route=True,
                    event_name="perception.stimuli",
                ),
                loop,
            )
