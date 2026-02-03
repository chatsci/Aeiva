import asyncio
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from aeiva.interface.gateway_base import GatewayBase
from aeiva.event.event_names import EventNames

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


@dataclass(frozen=True)
class WhatsAppRoute:
    phone_number: str
    display_name: Optional[str] = None


class WhatsAppGateway(GatewayBase[WhatsAppRoute]):
    """
    WhatsApp Cloud API gateway that bridges WhatsApp messages to AEIVA EventBus.

    Inbound:  WhatsApp webhook POST -> perception.stimuli (Signal source=perception.whatsapp)
    Outbound: cognition.thought -> WhatsApp reply via Meta Graph API

    Route resolution strategy (mirrors SlackGateway):
    1. Store route by original Signal trace_id.
    2. Subscribe to perception.output to chain trace_ids through perception.
    3. On cognition.thought, look up route via Signal parent_id chain.
    4. Fallback: use pending FIFO queue when source indicates WhatsApp.
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
        self._stop_event = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Tokens
        self._access_token: Optional[str] = None
        self._verify_token: Optional[str] = None
        self._phone_number_id: Optional[str] = None

        # Message dedup: bounded set of recently seen message IDs
        self._seen_ids: "OrderedDict[str, None]" = OrderedDict()
        self._max_dedup = int(self.config.get("max_message_dedup", 10000))

        # FastAPI app (created lazily in get_fastapi_app)
        self._app: Optional[FastAPI] = None

    async def setup(self) -> None:
        self._access_token = self._resolve_token(
            "access_token", "access_token_env_var", "WHATSAPP_ACCESS_TOKEN"
        )
        self._verify_token = self._resolve_token(
            "verify_token", "verify_token_env_var", "WHATSAPP_VERIFY_TOKEN"
        )
        self._phone_number_id = self._resolve_token(
            "phone_number_id", "phone_number_id_env_var", "WHATSAPP_PHONE_NUMBER_ID"
        )

        if not self._access_token:
            raise ValueError(
                "WhatsApp access token missing. "
                "Set whatsapp_config.access_token or WHATSAPP_ACCESS_TOKEN env var."
            )
        if not self._verify_token:
            raise ValueError(
                "WhatsApp verify token missing. "
                "Set whatsapp_config.verify_token or WHATSAPP_VERIFY_TOKEN env var."
            )
        if not self._phone_number_id:
            raise ValueError(
                "WhatsApp phone_number_id missing. "
                "Set whatsapp_config.phone_number_id or WHATSAPP_PHONE_NUMBER_ID env var."
            )

        self._loop = asyncio.get_running_loop()
        logger.info(
            "WhatsApp gateway ready (phone_number_id=%s).",
            self._phone_number_id,
        )

        self.register_handlers()

    def get_fastapi_app(self) -> FastAPI:
        if self._app is not None:
            return self._app

        app = FastAPI(title="Aeiva WhatsApp Gateway")
        webhook_path = self.config.get("webhook_path", "/webhook")

        @app.get(webhook_path, response_class=PlainTextResponse)
        async def verify_webhook(
            request: Request,
        ) -> Any:
            mode = request.query_params.get("hub.mode")
            token = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")
            return self._verify_webhook(mode, token, challenge)

        @app.post(webhook_path)
        async def receive_webhook(request: Request) -> Dict[str, str]:
            body = await request.json()
            await self._handle_incoming(body)
            return {"status": "ok"}

        self._app = app
        return app

    async def run(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        import uvicorn

        app = self.get_fastapi_app()
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)

        # Run server until stop_event is set
        serve_task = asyncio.create_task(server.serve())
        stop_task = asyncio.create_task(self._stop_event.wait())

        done, pending = await asyncio.wait(
            [serve_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        server.should_exit = True
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    async def stop(self) -> None:
        self._stop_event.set()

    def request_stop(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        else:
            self._stop_event.set()

    # ------------------------------------------------------------------
    # Webhook verification
    # ------------------------------------------------------------------

    def _verify_webhook(
        self,
        mode: Optional[str],
        token: Optional[str],
        challenge: Optional[str],
    ) -> Any:
        if mode == "subscribe" and token == self._verify_token:
            logger.info("WhatsApp webhook verified.")
            return PlainTextResponse(content=challenge or "", status_code=200)
        logger.warning("WhatsApp webhook verification failed (mode=%s).", mode)
        return PlainTextResponse(content="Forbidden", status_code=403)

    # ------------------------------------------------------------------
    # Inbound: WhatsApp -> Agent
    # ------------------------------------------------------------------

    async def _handle_incoming(self, body: Dict[str, Any]) -> None:
        entries = body.get("entry") or []
        for entry in entries:
            changes = entry.get("changes") or []
            for change in changes:
                value = change.get("value") or {}
                messages = value.get("messages") or []
                contacts = value.get("contacts") or []
                contact_map = {
                    c.get("wa_id", ""): c.get("profile", {}).get("name", "")
                    for c in contacts
                }
                for msg in messages:
                    await self._process_message(msg, contact_map)

    async def _process_message(
        self, msg: Dict[str, Any], contact_map: Dict[str, str]
    ) -> None:
        msg_id = msg.get("id")
        if not msg_id:
            return

        # Dedup
        if msg_id in self._seen_ids:
            return
        self._seen_ids[msg_id] = None
        while len(self._seen_ids) > self._max_dedup:
            self._seen_ids.popitem(last=False)

        msg_type = msg.get("type")
        if msg_type != "text":
            logger.debug("Ignoring non-text WhatsApp message (type=%s).", msg_type)
            return

        text = (msg.get("text") or {}).get("body", "").strip()
        if not text:
            return

        sender = msg.get("from", "")
        display_name = contact_map.get(sender, "")

        logger.info(
            "WhatsApp message received (from=%s, name=%s).",
            sender,
            display_name,
        )
        await self._ingest_message(sender, display_name, text)

    async def _ingest_message(
        self, phone_number: str, display_name: str, text: str
    ) -> None:
        route = WhatsAppRoute(phone_number=phone_number, display_name=display_name)

        signal = self.build_input_signal(
            text,
            source=EventNames.PERCEPTION_WHATSAPP,
            route=route,
        )
        await self.emit_input(
            signal,
            route=route,
            add_pending_route=True,
            event_name=EventNames.PERCEPTION_STIMULI,
        )

    async def send_message(self, route: Optional[WhatsAppRoute], text: str) -> None:
        if not route:
            return
        logger.info("WhatsApp response sending (to=%s).", route.phone_number)
        await self._send_message(route, str(text))

    def matches_source(self, source: str) -> bool:
        return "whatsapp" in (source or "").lower()

    def route_user_id(self, route: Optional[WhatsAppRoute]) -> Optional[str]:
        if not route:
            return None
        return route.phone_number

    async def _send_message(self, route: WhatsAppRoute, text: str) -> None:
        if not self._access_token or not self._phone_number_id:
            return

        url = f"{GRAPH_API_BASE}/{self._phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": route.phone_number,
            "type": "text",
            "text": {"body": text},
        }

        try:
            resp = await asyncio.to_thread(
                requests.post, url, json=payload, headers=headers, timeout=30
            )
            if resp.status_code != 200:
                logger.error(
                    "WhatsApp send failed (status=%d): %s",
                    resp.status_code,
                    resp.text,
                )
            else:
                logger.debug("WhatsApp message sent to %s.", route.phone_number)
        except Exception as exc:
            logger.error("WhatsApp send error: %s", exc)

    # ------------------------------------------------------------------
    # Agent stop
    # ------------------------------------------------------------------

    async def _handle_agent_stop(self, event: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Token resolution
    # ------------------------------------------------------------------

    def _resolve_token(
        self, key: str, env_key: str, default_env: str
    ) -> Optional[str]:
        token = self.config.get(key)
        if token:
            return token
        env_var = self.config.get(env_key) or default_env
        if env_var:
            logger.warning("WhatsApp %s not set. Provide it directly in config.", key)
        return None
