import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

from aeiva.interface.gateway_base import GatewayBase
from aeiva.event.event_names import EventNames

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SlackRoute:
    channel: str
    thread_ts: Optional[str]
    user: Optional[str]


class SlackGateway(GatewayBase[SlackRoute]):
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
        super().__init__(
            config or {},
            event_bus,
            stream_mode="buffer",
            response_timeout=float((config or {}).get("response_timeout", 60.0)),
            max_routes=int((config or {}).get("max_route_cache", 2048)),
            pending_queue_max=int((config or {}).get("max_pending_routes", 256)),
        )
        self.config = config or {}
        self._client: Optional[SocketModeClient] = None
        self._web_client: Optional[AsyncWebClient] = None
        self._bot_user_id: Optional[str] = None
        self._stop_event = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

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

        self.register_handlers()

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
        if channel and channel.startswith("D"):
            reply_in_thread = False
        if reply_in_thread and not thread_ts:
            thread_ts = ts

        route = SlackRoute(channel=channel, thread_ts=thread_ts, user=user)

        signal = self.build_input_signal(
            text,
            source=EventNames.PERCEPTION_SLACK,
            route=route,
        )
        await self.emit_input(
            signal,
            route=route,
            add_pending_route=True,
            event_name=EventNames.PERCEPTION_STIMULI,
        )

        await self._ensure_home_view(user)

    async def send_message(self, route: Optional[SlackRoute], text: str) -> None:
        if not route:
            return
        logger.info("Slack response sending (channel=%s).", route.channel)
        await self._send_message(route, str(text))

    def matches_source(self, source: str) -> bool:
        return "slack" in (source or "").lower()

    def route_user_id(self, route: Optional[SlackRoute]) -> Optional[str]:
        if not route:
            return None
        return route.user

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
    # Token resolution
    # ------------------------------------------------------------------

    def _resolve_token(self, key: str, env_key: str, default_env: str) -> Optional[str]:
        token = self.config.get(key)
        if token:
            return token
        env_var = self.config.get(env_key) or default_env
        if env_var:
            logger.warning("Slack %s not set. Provide it directly in config.", key)
        return None
