import asyncio
import logging
import os
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

from aeiva.neuron import Signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SlackRoute:
    channel: str
    thread_ts: Optional[str]
    user: Optional[str]


class SlackGateway:
    """
    Slack Socket Mode gateway that bridges Slack messages to AEIVA EventBus.

    Inbound:  Slack message -> perception.stimuli (Signal source=perception.slack)
    Outbound: cognition.thought -> Slack reply

    Route resolution strategy:
    1. Store route by original Signal trace_id.
    2. Subscribe to perception.output to chain trace_ids through perception.
    3. On cognition.thought, look up route via Signal parent_id chain.
    4. Fallback: use pending FIFO queue when source indicates Slack.
    5. For streaming: accumulate chunks, send assembled text on final.
    """

    def __init__(self, config: Dict[str, Any], event_bus: Any) -> None:
        self.config = config or {}
        self.events = event_bus
        self._client: Optional[SocketModeClient] = None
        self._web_client: Optional[AsyncWebClient] = None
        self._bot_user_id: Optional[str] = None
        self._stop_event = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Route cache: trace_id -> SlackRoute
        self._routes: "OrderedDict[str, SlackRoute]" = OrderedDict()
        self._routes_lock = asyncio.Lock()
        self._max_routes = int(self.config.get("max_route_cache", 2048))

        # Pending FIFO queue for fallback routing (serial conversations)
        self._pending_slack: deque[SlackRoute] = deque(maxlen=256)
        self._pending_lock = asyncio.Lock()

        # Streaming buffer: accumulate chunks before sending
        self._streaming_chunks: List[str] = []
        self._streaming_route: Optional[SlackRoute] = None

        # Home view
        self._home_view_enabled = bool(self.config.get("home_view_enabled", True))
        self._home_published_for: set[str] = set()
        self._max_home_cache = int(self.config.get("max_home_cache", 512))

    async def setup(self) -> None:
        bot_token = self._resolve_token("bot_token", "bot_token_env_var", "SLACK_BOT_TOKEN")
        app_token = self._resolve_token("app_token", "app_token_env_var", "SLACK_APP_TOKEN")
        if not bot_token or not app_token:
            raise ValueError("Slack bot/app token missing. Set slack_config bot_token/app_token or env vars.")

        self._web_client = AsyncWebClient(token=bot_token)
        self._client = SocketModeClient(app_token=app_token, web_client=self._web_client)
        self._client.socket_mode_request_listeners.append(self._handle_socket_mode_request)

        auth = await self._web_client.auth_test()
        self._bot_user_id = auth.get("user_id")
        self._loop = asyncio.get_running_loop()
        logger.info("Slack gateway ready (bot_user_id=%s).", self._bot_user_id)

        if self.events:
            self.events.subscribe("perception.output", self._handle_perception_output)
            self.events.subscribe("cognition.thought", self._handle_cognition_event)
            self.events.subscribe("agent.stop", self._handle_agent_stop)

    async def run(self) -> None:
        if not self._client:
            await self.setup()
        assert self._client is not None
        await self._client.connect()
        await self._stop_event.wait()
        await self._client.close()

    async def stop(self) -> None:
        self._stop_event.set()

    def request_stop(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        else:
            self._stop_event.set()

    # ------------------------------------------------------------------
    # Inbound: Slack -> Agent
    # ------------------------------------------------------------------

    async def _handle_socket_mode_request(self, client: SocketModeClient, req: SocketModeRequest) -> None:
        if req.type != "events_api":
            await client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
            return

        await client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
        event = (req.payload or {}).get("event") or {}
        if event.get("type") == "app_home_opened":
            if self._home_view_enabled and event.get("tab") == "home":
                await self._publish_home_view(event)
            return

        event_type = event.get("type")
        if event_type not in {"message", "app_mention"}:
            return
        if event_type == "message" and (event.get("subtype") or event.get("bot_id")):
            return
        if self._bot_user_id and event.get("user") == self._bot_user_id:
            return

        channel = event.get("channel")
        if not channel:
            return
        allowed = self.config.get("allowed_channels") or []
        if allowed and channel not in allowed:
            return

        text = event.get("text") or ""
        # Strip bot mention (e.g., "<@U12345> hello" -> "hello")
        if self._bot_user_id:
            mention = f"<@{self._bot_user_id}>"
            if text.startswith(mention):
                text = text[len(mention):].strip()
        if not text.strip():
            return

        logger.info("Slack message received (type=%s, channel=%s, user=%s).", event_type, channel, event.get("user"))
        await self._ingest_message(event, text)

    async def _ingest_message(self, event: Dict[str, Any], text: str) -> None:
        channel = event.get("channel")
        user = event.get("user")
        ts = event.get("ts")
        thread_ts = event.get("thread_ts")
        reply_in_thread = bool(self.config.get("reply_in_thread", True))
        if reply_in_thread and not thread_ts:
            thread_ts = ts

        route = SlackRoute(channel=channel, thread_ts=thread_ts, user=user)

        signal = Signal(source="perception.slack", data=text)
        await self._remember_route(signal.trace_id, route)
        async with self._pending_lock:
            self._pending_slack.append(route)

        await self._ensure_home_view(user)
        if self.events:
            await self.events.emit("perception.stimuli", payload=signal)

    # ------------------------------------------------------------------
    # Trace-id chaining: intercept perception.output to extend route map
    # ------------------------------------------------------------------

    async def _handle_perception_output(self, event: Any) -> None:
        """When perception.output fires, its parent_id points to our original
        gateway Signal.  Store the route under this new trace_id so that the
        next hop (cognition) can find it via parent_id."""
        payload = event.payload
        if not isinstance(payload, Signal):
            return
        parent_id = payload.parent_id
        if not parent_id:
            return
        route = await self._get_route(parent_id, pop=False)
        if route:
            await self._remember_route(payload.trace_id, route)

    # ------------------------------------------------------------------
    # Outbound: Agent -> Slack
    # ------------------------------------------------------------------

    async def _handle_cognition_event(self, event: Any) -> None:
        payload = event.payload
        if isinstance(payload, Signal):
            data = payload.data if isinstance(payload.data, dict) else {"text": str(payload.data)}
        elif isinstance(payload, dict):
            data = payload
        else:
            return

        # --- Streaming handling ---
        if data.get("streaming"):
            await self._handle_streaming_chunk(data, payload)
            return

        # --- Non-streaming (complete response) ---
        # Skip the streaming_complete signal for the UI (but we DO want it)
        text = data.get("thought") or data.get("output") or data.get("text")
        if not text:
            return

        route = await self._resolve_route(payload)
        if not route:
            return

        logger.info("Slack response sending (channel=%s).", route.channel)
        await self._send_message(route, str(text))

    async def _handle_streaming_chunk(self, data: Dict[str, Any], payload: Any) -> None:
        """Accumulate streaming chunks; send assembled text on final=True."""
        is_final = bool(data.get("final", False))

        if not is_final:
            chunk = data.get("thought", "")
            if chunk:
                self._streaming_chunks.append(chunk)
            # On first chunk, resolve and cache the route
            if self._streaming_route is None:
                self._streaming_route = await self._resolve_route(payload)
            return

        # Final chunk: assemble and send
        text = "".join(self._streaming_chunks).strip()
        route = self._streaming_route
        self._streaming_chunks.clear()
        self._streaming_route = None

        if not text or not route:
            return

        logger.info("Slack streaming response sending (channel=%s, len=%d).", route.channel, len(text))
        await self._send_message(route, text)

    async def _resolve_route(self, payload: Any) -> Optional[SlackRoute]:
        """Try to find the SlackRoute for this response."""
        # 1. Try trace_id chain via Signal parent_id
        if isinstance(payload, Signal) and payload.parent_id:
            route = await self._get_route(payload.parent_id, pop=True)
            if route:
                return route

        # 2. Try origin_trace_id field (set by Cognition for lineage tracking)
        origin = None
        if isinstance(payload, Signal) and isinstance(payload.data, dict):
            origin = payload.data.get("origin_trace_id")
        elif isinstance(payload, dict):
            origin = payload.get("origin_trace_id")
        if origin:
            route = await self._get_route(origin, pop=True)
            if route:
                return route

        # 3. Check if source indicates Slack, use pending FIFO
        source = ""
        if isinstance(payload, Signal):
            source = payload.data.get("source", "") if isinstance(payload.data, dict) else ""
            if not source:
                source = payload.source or ""
        elif isinstance(payload, dict):
            source = payload.get("source", "")

        if "slack" in source.lower():
            async with self._pending_lock:
                if self._pending_slack:
                    return self._pending_slack.popleft()

        return None

    async def _send_message(self, route: SlackRoute, text: str) -> None:
        if not self._web_client:
            return
        kwargs: Dict[str, Any] = {"channel": route.channel, "text": text}
        if route.thread_ts:
            kwargs["thread_ts"] = route.thread_ts
        try:
            await self._web_client.chat_postMessage(**kwargs)
        except Exception as exc:
            logger.error("Slack postMessage failed: %s", exc)

    # ------------------------------------------------------------------
    # Agent stop
    # ------------------------------------------------------------------

    async def _handle_agent_stop(self, event: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Home view
    # ------------------------------------------------------------------

    async def _publish_home_view(self, event: Dict[str, Any]) -> None:
        if not self._web_client:
            return
        user_id = event.get("user")
        if not user_id:
            return
        await self._publish_home_view_for_user(user_id)

    async def _ensure_home_view(self, user_id: Optional[str]) -> None:
        if not self._home_view_enabled or not user_id:
            return
        if user_id in self._home_published_for:
            return
        await self._publish_home_view_for_user(user_id)

    async def _publish_home_view_for_user(self, user_id: str) -> None:
        if not self._web_client:
            return
        view = self._build_home_view()
        try:
            await self._web_client.views_publish(user_id=user_id, view=view)
            self._home_published_for.add(user_id)
            if len(self._home_published_for) > self._max_home_cache:
                self._home_published_for.pop()
        except Exception as exc:
            logger.error("Slack home view publish failed: %s", exc)

    def _build_home_view(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        title = self.config.get("home_title") or "Aeiva"
        subtitle = self.config.get("home_subtitle") or "Agent is online."
        return {
            "type": "home",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": title},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": subtitle},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Last updated:* {now}"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "You can DM me here or mention me in a channel.",
                    },
                },
            ],
        }

    # ------------------------------------------------------------------
    # Route cache helpers
    # ------------------------------------------------------------------

    async def _remember_route(self, trace_id: str, route: SlackRoute) -> None:
        async with self._routes_lock:
            self._routes[trace_id] = route
            while len(self._routes) > self._max_routes:
                self._routes.popitem(last=False)

    async def _get_route(self, trace_id: str, *, pop: bool = False) -> Optional[SlackRoute]:
        async with self._routes_lock:
            if pop:
                return self._routes.pop(trace_id, None)
            return self._routes.get(trace_id)

    # ------------------------------------------------------------------
    # Token resolution
    # ------------------------------------------------------------------

    def _resolve_token(self, key: str, env_key: str, default_env: str) -> Optional[str]:
        token = self.config.get(key)
        if token:
            return token
        env_var = self.config.get(env_key) or default_env
        return os.getenv(env_var)
