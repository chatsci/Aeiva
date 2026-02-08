from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, Mapping, Optional, Sequence, Tuple
from uuid import uuid4

from .spec_normalizer import normalize_metaui_patch, normalize_metaui_spec
from .protocol import MetaUICommand, MetaUIEvent, MetaUISpec, new_command_id
from .session import MetaUIPhase, MetaUISession
from .upload_store import UploadStore, UploadStoreConfig
from .a2ui_runtime import evaluate_check_definitions
from .a2ui_protocol import CatalogSnapshot, ClientHello, HelloAck
from .capabilities import (
    MetaUIClientCapabilities,
    build_catalog_snapshot,
    negotiate_client_capabilities,
)
from .component_catalog import get_component_catalog
from .lifecycle_messages import (
    build_data_model_update_message,
    build_delete_surface_message,
    build_ui_render_sequence,
)

logger = logging.getLogger(__name__)

try:
    from websockets.server import serve  # type: ignore
except Exception:  # pragma: no cover - compatibility fallback
    try:
        from websockets.legacy.server import serve  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        serve = None


@dataclass(frozen=True)
class MetaUIEndpoint:
    host: str
    port: int
    ws_url: str
    token_required: bool


@dataclass(frozen=True)
class MetaUIRuntimeSettings:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8765
    token: Optional[str] = None
    auto_ui: bool = True
    upload_base_dir: str = "storage/metaui/uploads"
    upload_max_file_bytes: int = 8 * 1024 * 1024
    upload_max_total_bytes: int = 24 * 1024 * 1024
    upload_max_files_per_event: int = 12
    hello_timeout_seconds: float = 2.0
    send_timeout_seconds: float = 1.0
    wait_ack_seconds: float = 0.3
    event_history_limit: int = 4096


@dataclass
class _AckWaiter:
    expected: int
    future: asyncio.Future[None]


@dataclass
class _AckState:
    count: int
    seen_at: float


@dataclass
class _ClientConnection:
    websocket: Any
    capabilities: MetaUIClientCapabilities
    connected_at: float


class MetaUIOrchestrator:
    """
    Local WebSocket orchestrator for MetaUI desktop sessions.

    Responsibilities:
    - Track UI sessions and explicit phase transitions.
    - Broadcast render/state commands to connected desktop clients.
    - Persist uploaded file payloads into a sandboxed local store.
    - Buffer and query UI events for downstream agents/tools.
    """

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: Optional[str] = None,
        auto_ui: bool = True,
        hello_timeout_seconds: float = 5.0,
        send_timeout_seconds: float = 2.5,
        wait_ack_seconds: float = 0.9,
        event_history_limit: int = 4096,
        upload_store: Optional[UploadStore] = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.token = (token or "").strip() or None
        self._auto_ui = bool(auto_ui)
        self.hello_timeout_seconds = max(0.5, float(hello_timeout_seconds))
        self.send_timeout_seconds = max(0.2, float(send_timeout_seconds))
        self.wait_ack_seconds = max(0.0, float(wait_ack_seconds))
        self.event_history_limit = max(64, int(event_history_limit))

        self._server: Any = None
        self._endpoint: Optional[MetaUIEndpoint] = None
        self._state_lock = asyncio.Lock()
        self._events_cond = asyncio.Condition()
        self._clients: Dict[str, _ClientConnection] = {}
        self._client_ready = asyncio.Event()

        self._sessions: Dict[str, MetaUISession] = {}
        self._event_history: Deque[MetaUIEvent] = deque(maxlen=self.event_history_limit)
        self._recent_event_ids: Deque[str] = deque(maxlen=self.event_history_limit)
        self._recent_event_id_set: set[str] = set()

        self._ack_state_ttl_seconds = max(30.0, self.wait_ack_seconds * 20.0)
        self._ack_state_max_entries = 4096
        self._ack_states_by_command_id: Dict[str, _AckState] = {}
        self._ack_waiters: Dict[str, _AckWaiter] = {}

        self._upload_store = upload_store or UploadStore(
            UploadStoreConfig(base_dir=Path("storage/metaui/uploads"))
        )

    async def start(self) -> MetaUIEndpoint:
        if self._server is not None and self._endpoint is not None:
            return self._endpoint
        if serve is None:
            raise RuntimeError(
                "MetaUI requires the `websockets` package. Install optional dependencies with `metaui` extra."
            )

        self._server = await serve(self._handle_connection, self.host, self.port)
        sockets = getattr(self._server, "sockets", None) or []
        if not sockets:
            raise RuntimeError("MetaUI server started without any bound socket.")

        bound_host, bound_port = sockets[0].getsockname()[:2]
        ws_url = f"ws://{bound_host}:{bound_port}/metaui"
        self._endpoint = MetaUIEndpoint(
            host=str(bound_host),
            port=int(bound_port),
            ws_url=ws_url,
            token_required=bool(self.token),
        )
        logger.info("MetaUI orchestrator started at %s", ws_url)
        return self._endpoint

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self._endpoint = None
        async with self._state_lock:
            self._clients.clear()
            self._client_ready.clear()
            for waiter in self._ack_waiters.values():
                if not waiter.future.done():
                    waiter.future.set_result(None)
            self._ack_states_by_command_id.clear()
            self._ack_waiters.clear()
            self._recent_event_ids.clear()
            self._recent_event_id_set.clear()

    async def ensure_started(self) -> MetaUIEndpoint:
        return await self.start()

    async def wait_for_client(self, timeout: float = 5.0) -> bool:
        try:
            await asyncio.wait_for(self._client_ready.wait(), timeout=max(0.1, float(timeout)))
            return True
        except asyncio.TimeoutError:
            return False

    async def status(self) -> Dict[str, Any]:
        endpoint = await self.ensure_started()
        async with self._state_lock:
            phases: Dict[str, int] = {}
            for session in self._sessions.values():
                phase_name = session.phase.value
                phases[phase_name] = phases.get(phase_name, 0) + 1
            return {
                "success": True,
                "running": True,
                "ws_url": endpoint.ws_url,
                "host": endpoint.host,
                "port": endpoint.port,
                "token_required": endpoint.token_required,
                "connected_clients": len(self._clients),
                "active_ui_sessions": len(self._sessions),
                "session_phases": phases,
                "auto_ui": self._auto_ui,
                "event_history_size": len(self._event_history),
            }

    async def set_auto_ui(self, enabled: bool) -> Dict[str, Any]:
        self._auto_ui = bool(enabled)
        return {"success": True, "auto_ui": self._auto_ui}

    async def list_sessions(self) -> Dict[str, Any]:
        async with self._state_lock:
            items = [session.to_dict() for session in self._sessions.values()]
        items.sort(key=lambda item: item["updated_at"], reverse=True)
        return {"success": True, "sessions": items}

    async def get_session(self, ui_id: str) -> Dict[str, Any]:
        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session is None:
                return {"success": False, "error": f"unknown ui_id: {ui_id}"}
            session_snapshot = session.to_dict()
            session_snapshot["state"] = deepcopy(session.state)
            return {
                "success": True,
                "session": session_snapshot,
                "spec": session.spec.model_dump(mode="json"),
            }

    async def update_phase(
        self,
        *,
        ui_id: str,
        phase: str,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            target = MetaUIPhase(str(phase).strip().lower())
        except Exception:
            return {"success": False, "error": f"invalid phase: {phase}"}

        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session is None:
                return {"success": False, "error": f"unknown ui_id: {ui_id}"}
            session.update_phase(target, error=error)

        return {"success": True, "ui_id": ui_id, "phase": target.value}

    async def get_events(
        self,
        *,
        ui_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_types: Optional[Sequence[str]] = None,
        since_ts: Optional[float] = None,
        limit: int = 50,
        consume: bool = False,
    ) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 500))
        type_set = {item for item in (event_types or []) if isinstance(item, str) and item.strip()}

        async with self._state_lock:
            selected: list[MetaUIEvent] = []
            kept: Deque[MetaUIEvent] = deque(maxlen=self.event_history_limit)
            for event in self._event_history:
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
                if len(selected) < limit:
                    selected.append(event)
                else:
                    kept.append(event)
            if consume and selected:
                self._event_history = kept

        return {
            "success": True,
            "events": [event.model_dump(mode="json") for event in selected],
            "count": len(selected),
            "consumed": bool(consume and selected),
        }

    async def wait_event(
        self,
        *,
        ui_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_types: Optional[Sequence[str]] = None,
        timeout: float = 30.0,
        consume: bool = True,
    ) -> Dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + max(0.1, float(timeout))
        while True:
            batch = await self.get_events(
                ui_id=ui_id,
                session_id=session_id,
                event_types=event_types,
                limit=1,
                consume=consume,
            )
            if batch["events"]:
                return {"success": True, "event": batch["events"][0], "consumed": batch["consumed"]}

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return {"success": False, "error": "timeout", "event": None}

            async with self._events_cond:
                try:
                    await asyncio.wait_for(self._events_cond.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    return {"success": False, "error": "timeout", "event": None}

    async def render_full(
        self,
        *,
        spec: Dict[str, Any] | MetaUISpec,
        session_id: Optional[str] = None,
        ui_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        validated = (
            spec
            if isinstance(spec, MetaUISpec)
            else MetaUISpec.model_validate(normalize_metaui_spec(spec, strict_component_types=True))
        )
        if ui_id:
            validated.ui_id = ui_id
        if session_id:
            validated.session_id = session_id

        session = MetaUISession(
            ui_id=validated.ui_id,
            session_id=validated.session_id,
            spec=validated,
            phase=MetaUIPhase.RENDERING,
        )
        async with self._state_lock:
            self._sessions[validated.ui_id] = session

        result = await self._broadcast_render_full_session(session=session, expect_ack=True)

        async with self._state_lock:
            existing = self._sessions.get(validated.ui_id)
            if existing:
                if result["success"]:
                    existing.update_phase(MetaUIPhase.INTERACTIVE)
                else:
                    existing.update_phase(MetaUIPhase.RECOVERING, error=result.get("error"))
        return result

    async def patch(
        self,
        *,
        ui_id: str,
        patch: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_patch = normalize_metaui_patch(patch)
        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session is None:
                return {"success": False, "error": f"unknown ui_id: {ui_id}"}
            session.update_phase(MetaUIPhase.RENDERING)
            session.bump_version()
        command = MetaUICommand(
            command="patch",
            ui_id=ui_id,
            session_id=session_id,
            payload={"patch": normalized_patch},
        )
        result = await self._broadcast(command, expect_ack=True)
        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session:
                if result["success"]:
                    session.update_phase(MetaUIPhase.INTERACTIVE)
                else:
                    session.update_phase(MetaUIPhase.RECOVERING, error=result.get("error"))
        return result

    async def set_state(
        self,
        *,
        ui_id: str,
        state: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session is None:
                return {"success": False, "error": f"unknown ui_id: {ui_id}"}
            session.state = self._deep_merge_dicts(session.state, state)
            session.bump_version()
        return await self._broadcast_state_update(
            ui_id=ui_id,
            session_id=session_id,
            state_patch=state,
        )

    async def notify(
        self,
        *,
        ui_id: Optional[str],
        message: str,
        level: str = "info",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        command = MetaUICommand(
            command="notify",
            ui_id=ui_id,
            session_id=session_id,
            payload={"message": message, "level": level},
        )
        return await self._broadcast(command, expect_ack=False)

    async def close(
        self,
        *,
        ui_id: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self._state_lock:
            self._sessions.pop(ui_id, None)
        return await self._broadcast_close(ui_id=ui_id, session_id=session_id)

    async def _broadcast(self, command: MetaUICommand, *, expect_ack: bool) -> Dict[str, Any]:
        endpoint = await self.ensure_started()
        payload = json.dumps(command.model_dump(mode="json"), ensure_ascii=False)

        async with self._state_lock:
            self._prune_ack_state(now=asyncio.get_running_loop().time())
            clients = list(self._clients.items())

        if not clients:
            return {
                "success": False,
                "error": "no_connected_clients",
                "command_id": command.command_id,
                "ui_id": command.ui_id,
                "ws_url": endpoint.ws_url,
                "sent": 0,
                "acks": 0,
            }

        sent = 0
        stale_clients: list[str] = []
        for client_id, connection in clients:
            try:
                await asyncio.wait_for(connection.websocket.send(payload), timeout=self.send_timeout_seconds)
                sent += 1
            except Exception as exc:  # pragma: no cover - transport edge
                logger.debug("MetaUI send failed (%s): %s", client_id, exc)
                stale_clients.append(client_id)

        if stale_clients:
            async with self._state_lock:
                for client_id in stale_clients:
                    self._clients.pop(client_id, None)
                if not self._clients:
                    self._client_ready.clear()

        ack_count = await self._await_ack(command_id=command.command_id, sent=sent, expect_ack=expect_ack)

        return {
            "success": sent > 0,
            "command_id": command.command_id,
            "ui_id": command.ui_id,
            "session_id": command.session_id,
            "ws_url": endpoint.ws_url,
            "sent": sent,
            "connected_clients": len(clients) - len(stale_clients),
            "acks": ack_count,
        }

    async def _await_ack(self, *, command_id: str, sent: int, expect_ack: bool) -> int:
        ack_count = self._ack_count(command_id)
        if not expect_ack or sent <= 0 or self.wait_ack_seconds <= 0:
            return ack_count

        waiter = _AckWaiter(
            expected=1,
            future=asyncio.get_running_loop().create_future(),
        )
        async with self._state_lock:
            self._ack_waiters[command_id] = waiter
        try:
            await asyncio.wait_for(waiter.future, timeout=self.wait_ack_seconds)
        except asyncio.TimeoutError:
            pass
        finally:
            async with self._state_lock:
                self._ack_waiters.pop(command_id, None)
        return self._ack_count(command_id)

    @staticmethod
    def _supports_a2ui_stream(connection: _ClientConnection) -> bool:
        capabilities = connection.capabilities
        if not capabilities.supports_feature("a2ui_stream_v1"):
            return False
        supported_commands = set(capabilities.supported_commands)
        if not supported_commands:
            return True
        required = {"surface_update", "data_model_update", "begin_rendering", "delete_surface"}
        return required.issubset(supported_commands)

    async def _send_payloads_to_clients(
        self,
        *,
        payloads_by_client: Dict[str, Sequence[Dict[str, Any]]],
        command_id: str,
        ui_id: Optional[str],
        session_id: Optional[str],
        expect_ack: bool,
    ) -> Dict[str, Any]:
        endpoint = await self.ensure_started()
        async with self._state_lock:
            self._prune_ack_state(now=asyncio.get_running_loop().time())
            clients = list(self._clients.items())

        if not clients:
            return {
                "success": False,
                "error": "no_connected_clients",
                "command_id": command_id,
                "ui_id": ui_id,
                "session_id": session_id,
                "ws_url": endpoint.ws_url,
                "sent": 0,
                "acks": 0,
            }

        sent = 0
        stale_clients: list[str] = []
        for client_id, connection in clients:
            payloads = payloads_by_client.get(client_id) or ()
            if not payloads:
                continue
            try:
                for payload in payloads:
                    await asyncio.wait_for(
                        connection.websocket.send(json.dumps(payload, ensure_ascii=False)),
                        timeout=self.send_timeout_seconds,
                    )
                sent += 1
            except Exception as exc:  # pragma: no cover - transport edge
                logger.debug("MetaUI send failed (%s): %s", client_id, exc)
                stale_clients.append(client_id)

        if stale_clients:
            async with self._state_lock:
                for client_id in stale_clients:
                    self._clients.pop(client_id, None)
                if not self._clients:
                    self._client_ready.clear()

        ack_count = await self._await_ack(command_id=command_id, sent=sent, expect_ack=expect_ack)
        return {
            "success": sent > 0,
            "command_id": command_id,
            "ui_id": ui_id,
            "session_id": session_id,
            "ws_url": endpoint.ws_url,
            "sent": sent,
            "connected_clients": len(clients) - len(stale_clients),
            "acks": ack_count,
        }

    def _build_render_payloads_for_client(
        self,
        *,
        connection: _ClientConnection,
        session: MetaUISession,
        command_id: str,
        include_state: bool,
    ) -> Sequence[Dict[str, Any]]:
        if self._supports_a2ui_stream(connection):
            sequence = build_ui_render_sequence(
                spec=session.spec,
                state=session.state if include_state and session.state else None,
                catalog_id=build_catalog_snapshot(get_component_catalog())["catalogId"],
            )
            if sequence:
                sequence[-1] = dict(sequence[-1])
                sequence[-1]["command_id"] = command_id
            return sequence

        payloads: list[Dict[str, Any]] = [
            MetaUICommand(
                command="render_full",
                ui_id=session.ui_id,
                session_id=session.session_id,
                command_id=command_id,
                payload=session.spec.model_dump(mode="json"),
            ).model_dump(mode="json")
        ]
        if include_state and session.state:
            payloads.append(
                MetaUICommand(
                    command="set_state",
                    ui_id=session.ui_id,
                    session_id=session.session_id,
                    payload={"state": session.state},
                ).model_dump(mode="json")
            )
        return payloads

    async def _broadcast_render_full_session(
        self,
        *,
        session: MetaUISession,
        expect_ack: bool,
    ) -> Dict[str, Any]:
        command_id = new_command_id()
        async with self._state_lock:
            clients = dict(self._clients)
        payloads_by_client: Dict[str, Sequence[Dict[str, Any]]] = {}
        for client_id, connection in clients.items():
            payloads_by_client[client_id] = self._build_render_payloads_for_client(
                connection=connection,
                session=session,
                command_id=command_id,
                include_state=True,
            )
        return await self._send_payloads_to_clients(
            payloads_by_client=payloads_by_client,
            command_id=command_id,
            ui_id=session.ui_id,
            session_id=session.session_id,
            expect_ack=expect_ack,
        )

    async def _broadcast_state_update(
        self,
        *,
        ui_id: str,
        session_id: Optional[str],
        state_patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        command_id = new_command_id()
        async with self._state_lock:
            clients = dict(self._clients)

        payloads_by_client: Dict[str, Sequence[Dict[str, Any]]] = {}
        for client_id, connection in clients.items():
            if self._supports_a2ui_stream(connection):
                payloads_by_client[client_id] = (
                    build_data_model_update_message(
                        surface_id=ui_id,
                        state_patch=state_patch,
                        path="/",
                    ),
                )
                continue
            payloads_by_client[client_id] = (
                MetaUICommand(
                    command="set_state",
                    ui_id=ui_id,
                    session_id=session_id,
                    command_id=command_id,
                    payload={"state": state_patch},
                ).model_dump(mode="json"),
            )

        return await self._send_payloads_to_clients(
            payloads_by_client=payloads_by_client,
            command_id=command_id,
            ui_id=ui_id,
            session_id=session_id,
            expect_ack=False,
        )

    async def _broadcast_close(
        self,
        *,
        ui_id: str,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        command_id = new_command_id()
        async with self._state_lock:
            clients = dict(self._clients)

        payloads_by_client: Dict[str, Sequence[Dict[str, Any]]] = {}
        for client_id, connection in clients.items():
            if self._supports_a2ui_stream(connection):
                payloads_by_client[client_id] = (build_delete_surface_message(surface_id=ui_id),)
                continue
            payloads_by_client[client_id] = (
                MetaUICommand(
                    command="close",
                    ui_id=ui_id,
                    session_id=session_id,
                    command_id=command_id,
                    payload={},
                ).model_dump(mode="json"),
            )

        return await self._send_payloads_to_clients(
            payloads_by_client=payloads_by_client,
            command_id=command_id,
            ui_id=ui_id,
            session_id=session_id,
            expect_ack=False,
        )

    async def _handle_connection(self, websocket: Any, path: Optional[str] = None) -> None:
        if path and path not in {"/", "/metaui"}:
            await websocket.close(code=1008, reason="unsupported path")
            return

        raw_hello = await self._recv_json(websocket, timeout=self.hello_timeout_seconds)
        if not isinstance(raw_hello, dict) or raw_hello.get("type") != "hello":
            await websocket.close(code=1008, reason="missing hello")
            return

        try:
            hello = ClientHello.model_validate(raw_hello)
        except Exception:
            await websocket.close(code=1008, reason="invalid hello payload")
            return

        if self.token and hello.token != self.token:
            await websocket.close(code=4401, reason="unauthorized")
            return

        client_id = str(hello.client_id or f"metaui-client-{uuid4().hex[:8]}")
        catalog = get_component_catalog()
        negotiated = negotiate_client_capabilities(
            hello_payload=hello.model_dump(mode="json"),
            server_catalog=catalog,
        )
        connection = _ClientConnection(
            websocket=websocket,
            capabilities=negotiated,
            connected_at=asyncio.get_running_loop().time(),
        )
        async with self._state_lock:
            self._clients[client_id] = connection
            self._client_ready.set()

        hello_ack = HelloAck(
            client_id=client_id,
            protocol=negotiated.protocol_version,
            auto_ui=self._auto_ui,
            active_sessions=len(self._sessions),
            catalog=CatalogSnapshot.model_validate(build_catalog_snapshot(catalog)),
            negotiated_features=negotiated.features,
        )
        await websocket.send(
            json.dumps(hello_ack.model_dump(mode="json"), ensure_ascii=False)
        )
        await self._replay_sessions_to_client(connection)

        try:
            async for raw in websocket:
                message = self._decode_json(raw)
                if not isinstance(message, dict):
                    continue
                msg_type = message.get("type")
                if msg_type == "ack":
                    await self._record_ack(str(message.get("command_id") or ""))
                    continue
                if msg_type == "event":
                    await self._record_event(message)
        finally:
            async with self._state_lock:
                self._clients.pop(client_id, None)
                if not self._clients:
                    self._client_ready.clear()

    async def _replay_sessions_to_client(self, connection: _ClientConnection) -> None:
        async with self._state_lock:
            sessions = list(self._sessions.values())
        if not sessions:
            return

        sessions.sort(key=lambda item: float(item.updated_at))
        supports_multi_surface = self._supports_a2ui_stream(connection)
        replay_sessions = sessions if supports_multi_surface else [sessions[-1]]
        dropped = len(sessions) - len(replay_sessions)
        if dropped > 0:
            logger.debug(
                "MetaUI replay: legacy client cannot hold multiple surfaces; replaying latest only (dropped=%d).",
                dropped,
            )

        for session in replay_sessions:
            payloads = self._build_render_payloads_for_client(
                connection=connection,
                session=session,
                command_id=new_command_id(),
                include_state=True,
            )
            try:
                for payload in payloads:
                    await asyncio.wait_for(
                        connection.websocket.send(json.dumps(payload, ensure_ascii=False)),
                        timeout=self.send_timeout_seconds,
                    )
            except Exception as exc:
                logger.warning(
                    "MetaUI replay failed for ui_id=%s session_id=%s: %s",
                    session.ui_id,
                    session.session_id,
                    exc,
                )
                return

    async def _record_ack(self, command_id: str) -> None:
        if not command_id:
            return
        async with self._state_lock:
            now = asyncio.get_running_loop().time()
            state = self._ack_states_by_command_id.get(command_id)
            if state is None:
                state = self._new_ack_state(count=1, seen_at=now)
            else:
                state = self._new_ack_state(count=state.count + 1, seen_at=now)
            self._ack_states_by_command_id[command_id] = state
            self._prune_ack_state(now=now)
            count = state.count
            waiter = self._ack_waiters.get(command_id)
            if waiter and count >= waiter.expected and not waiter.future.done():
                waiter.future.set_result(None)

    @staticmethod
    def _new_ack_state(*, count: int, seen_at: float) -> _AckState:
        return _AckState(count=max(0, int(count)), seen_at=float(seen_at))

    def _ack_count(self, command_id: str) -> int:
        state = self._ack_states_by_command_id.get(command_id)
        return int(state.count) if state else 0

    def _prune_ack_state(self, *, now: Optional[float] = None) -> None:
        if not self._ack_states_by_command_id:
            return
        tick = float(now if now is not None else time.monotonic())
        stale_ids = [
            command_id
            for command_id, state in self._ack_states_by_command_id.items()
            if (tick - float(state.seen_at)) > self._ack_state_ttl_seconds
        ]
        for command_id in stale_ids:
            self._ack_states_by_command_id.pop(command_id, None)

        overflow = len(self._ack_states_by_command_id) - self._ack_state_max_entries
        if overflow <= 0:
            return
        ordered = sorted(
            self._ack_states_by_command_id.items(),
            key=lambda item: float(item[1].seen_at),
        )
        for command_id, _ in ordered[:overflow]:
            self._ack_states_by_command_id.pop(command_id, None)

    async def _record_event(self, event_payload: Dict[str, Any]) -> None:
        try:
            event = MetaUIEvent.model_validate(event_payload)
        except Exception:
            return

        async with self._state_lock:
            if event.event_id in self._recent_event_id_set:
                return
            if len(self._recent_event_ids) == self._recent_event_ids.maxlen:
                dropped = self._recent_event_ids[0]
                self._recent_event_id_set.discard(dropped)
            self._recent_event_ids.append(event.event_id)
            self._recent_event_id_set.add(event.event_id)

        if event.event_type == "upload":
            session_id = event.session_id or "default"
            files = event.payload.get("files")
            upload_result = self._upload_store.persist_files(
                files=files if isinstance(files, list) else [],
                session_id=session_id,
                event_id=event.event_id,
            )
            event.payload = dict(event.payload)
            event.payload["upload_result"] = upload_result

        async with self._state_lock:
            session = self._sessions.get(event.ui_id)
            if session:
                validation_errors = self._validate_event_checks(session=session, event=event)
                if validation_errors:
                    event.event_type = "error"
                    event.payload = dict(event.payload)
                    event.payload["code"] = "VALIDATION_FAILED"
                    event.payload["validation_errors"] = validation_errors

            self._event_history.append(event)
            if session:
                if event.event_type in {"submit", "action", "confirm", "retry"}:
                    session.update_phase(MetaUIPhase.EXECUTING)
                elif event.event_type in {"ready", "change", "upload"}:
                    session.update_phase(MetaUIPhase.INTERACTIVE)
                elif event.event_type in {"recover"}:
                    session.update_phase(MetaUIPhase.RECOVERING)
                elif event.event_type in {"error"}:
                    session.update_phase(MetaUIPhase.ERROR, error=str(event.payload.get("message") or "ui_error"))
                else:
                    session.updated_at = event.ts

        async with self._events_cond:
            self._events_cond.notify_all()

    @staticmethod
    def _find_component_by_id(spec: MetaUISpec, component_id: str) -> Mapping[str, Any] | None:
        target = str(component_id or "").strip()
        if not target:
            return None
        for component in spec.components:
            if component.id == target:
                return component.model_dump(mode="json")
        return None

    @staticmethod
    def _validate_input_component_checks(
        *,
        component_props: Mapping[str, Any],
        payload: Mapping[str, Any],
        state: Mapping[str, Any],
    ) -> list[str]:
        checks = component_props.get("checks")
        if not isinstance(checks, list) or not checks:
            return []
        value = payload.get("value")
        if value is None and "checked" in payload:
            value = payload.get("checked")
        context = {
            "payload": dict(payload),
            "form_values": dict(payload.get("values") or {}) if isinstance(payload.get("values"), Mapping) else {},
        }
        return evaluate_check_definitions(
            checks=checks,
            data_model=state,
            default_value=value,
            context=context,
        )

    @staticmethod
    def _validate_form_component_checks(
        *,
        component_props: Mapping[str, Any],
        payload: Mapping[str, Any],
        state: Mapping[str, Any],
    ) -> list[str]:
        values = payload.get("values")
        if not isinstance(values, Mapping):
            return []
        fields = component_props.get("fields")
        if not isinstance(fields, list):
            return []

        errors: list[str] = []
        form_values = dict(values)
        for field in fields:
            if not isinstance(field, Mapping):
                continue
            checks = field.get("checks")
            if not isinstance(checks, list) or not checks:
                continue
            field_id = str(field.get("id") or "").strip()
            default_value = form_values.get(field_id)
            context = {
                "payload": dict(payload),
                "form_values": form_values,
                "field_id": field_id,
            }
            errors.extend(
                evaluate_check_definitions(
                    checks=checks,
                    data_model=state,
                    default_value=default_value,
                    context=context,
                )
            )
        return errors

    def _validate_event_checks(self, *, session: MetaUISession, event: MetaUIEvent) -> list[str]:
        component = self._find_component_by_id(session.spec, event.component_id or "")
        if component is None:
            return []

        component_type = str(component.get("type") or "")
        props = component.get("props")
        if not isinstance(props, Mapping):
            return []
        payload = event.payload if isinstance(event.payload, Mapping) else {}
        state = session.state if isinstance(session.state, Mapping) else {}

        if component_type in {"input", "textarea", "select", "radio_group", "checkbox", "slider"}:
            return self._validate_input_component_checks(
                component_props=props,
                payload=payload,
                state=state,
            )
        if component_type in {"form", "form_step"}:
            return self._validate_form_component_checks(
                component_props=props,
                payload=payload,
                state=state,
            )
        return []

    async def _recv_json(self, websocket: Any, *, timeout: float) -> Any:
        raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
        return self._decode_json(raw)

    @staticmethod
    def _decode_json(raw: Any) -> Any:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        if not isinstance(raw, str):
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    @staticmethod
    def _deep_merge_dicts(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = dict(base or {})
        for key, value in (incoming or {}).items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = MetaUIOrchestrator._deep_merge_dicts(result[key], value)
            else:
                result[key] = value
        return result


_RUNTIME_SETTINGS = MetaUIRuntimeSettings()
_ORCHESTRATOR: Optional[MetaUIOrchestrator] = None


def _normalize_int(value: Any, default: int, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    if parsed < minimum:
        return default
    return parsed


def _normalize_float(value: Any, default: float, *, minimum: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    if parsed < minimum:
        return default
    return parsed


def configure_metaui_runtime(config_dict: Dict[str, Any]) -> None:
    """
    Configure process-wide MetaUI runtime defaults from AEIVA config.
    """
    global _RUNTIME_SETTINGS, _ORCHESTRATOR

    block = config_dict.get("metaui_config")
    if not isinstance(block, dict):
        return

    token = block.get("token")
    token_env_var = str(block.get("token_env_var") or "").strip()
    if not token and token_env_var:
        token = os.getenv(token_env_var)

    updated = replace(
        _RUNTIME_SETTINGS,
        enabled=bool(block.get("enabled", _RUNTIME_SETTINGS.enabled)),
        host=str(block.get("host") or _RUNTIME_SETTINGS.host),
        port=_normalize_int(block.get("port"), _RUNTIME_SETTINGS.port, minimum=0),
        token=((token or "").strip() or None),
        auto_ui=bool(block.get("auto_ui", _RUNTIME_SETTINGS.auto_ui)),
        upload_base_dir=str(block.get("upload_base_dir") or _RUNTIME_SETTINGS.upload_base_dir),
        upload_max_file_bytes=_normalize_int(
            block.get("upload_max_file_bytes"),
            _RUNTIME_SETTINGS.upload_max_file_bytes,
            minimum=1024,
        ),
        upload_max_total_bytes=_normalize_int(
            block.get("upload_max_total_bytes"),
            _RUNTIME_SETTINGS.upload_max_total_bytes,
            minimum=1024,
        ),
        upload_max_files_per_event=_normalize_int(
            block.get("upload_max_files_per_event"),
            _RUNTIME_SETTINGS.upload_max_files_per_event,
            minimum=1,
        ),
        hello_timeout_seconds=_normalize_float(
            block.get("hello_timeout_seconds"),
            _RUNTIME_SETTINGS.hello_timeout_seconds,
            minimum=0.2,
        ),
        send_timeout_seconds=_normalize_float(
            block.get("send_timeout_seconds"),
            _RUNTIME_SETTINGS.send_timeout_seconds,
            minimum=0.1,
        ),
        wait_ack_seconds=_normalize_float(
            block.get("wait_ack_seconds"),
            _RUNTIME_SETTINGS.wait_ack_seconds,
            minimum=0.0,
        ),
        event_history_limit=_normalize_int(
            block.get("event_history_limit"),
            _RUNTIME_SETTINGS.event_history_limit,
            minimum=64,
        ),
    )

    _RUNTIME_SETTINGS = updated
    _ORCHESTRATOR = None


def get_metaui_runtime_settings() -> MetaUIRuntimeSettings:
    return _RUNTIME_SETTINGS


def get_metaui_orchestrator(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    token: Optional[str] = None,
) -> MetaUIOrchestrator:
    global _ORCHESTRATOR

    settings = _RUNTIME_SETTINGS
    resolved_host = host or settings.host
    resolved_port = settings.port if port is None else int(port)
    resolved_token = token if token is not None else settings.token

    if _ORCHESTRATOR is None:
        upload_store = UploadStore(
            UploadStoreConfig(
                base_dir=Path(settings.upload_base_dir),
                max_file_bytes=settings.upload_max_file_bytes,
                max_total_bytes=settings.upload_max_total_bytes,
                max_files_per_event=settings.upload_max_files_per_event,
            )
        )
        _ORCHESTRATOR = MetaUIOrchestrator(
            host=resolved_host,
            port=resolved_port,
            token=resolved_token,
            auto_ui=settings.auto_ui,
            hello_timeout_seconds=settings.hello_timeout_seconds,
            send_timeout_seconds=settings.send_timeout_seconds,
            wait_ack_seconds=settings.wait_ack_seconds,
            event_history_limit=settings.event_history_limit,
            upload_store=upload_store,
        )
        return _ORCHESTRATOR

    same_endpoint = (
        _ORCHESTRATOR.host == resolved_host
        and _ORCHESTRATOR.port == resolved_port
        and _ORCHESTRATOR.token == ((resolved_token or "").strip() or None)
    )
    if same_endpoint:
        return _ORCHESTRATOR

    _ORCHESTRATOR = None
    return get_metaui_orchestrator(host=resolved_host, port=resolved_port, token=resolved_token)
