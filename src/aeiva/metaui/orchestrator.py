from __future__ import annotations

import asyncio
import json
import logging
import os
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
from uuid import uuid4

from .spec_normalizer import (
    collect_interaction_contract_issues,
    normalize_metaui_patch,
    normalize_metaui_spec,
)
from .update_strategy import apply_structural_patch_to_spec
from .protocol import MetaUICommand, MetaUIEvent, MetaUISpec, new_command_id
from .session import MetaUIPhase, MetaUISession
from .upload_store import UploadStore, UploadStoreConfig
from .a2ui_protocol import CatalogSnapshot, ClientHello, HelloAck
from .capabilities import (
    MetaUIClientCapabilities,
    build_catalog_snapshot,
    negotiate_client_capabilities,
)
from .event_pipeline import (
    event_validation_errors,
    find_validation_component,
    persist_event_uploads,
    sanitize_event_payload_in_place,
    translate_client_event_message,
)
from .a2ui_generation_contract import get_interaction_fix_guide
from .ack_tracker import AckTracker as _AckTracker, AckWaiter as _AckWaiter
from .component_catalog import get_component_catalog
from .data_model import merge_nested_dicts
from .lifecycle_messages import (
    build_data_model_update_message,
    build_delete_surface_message,
    build_ui_render_sequence,
)
from .error_codes import ERROR_ACK_TIMEOUT, ERROR_NO_CONNECTED_CLIENTS
from .event_store import MetaUIEventStore
from .session_store import list_sessions_sorted, phase_counts, snapshot_session

logger = logging.getLogger(__name__)


def _interaction_contract_error_payload(
    *,
    summary: str,
    issues: Sequence[str],
) -> Dict[str, Any]:
    return {
        "success": False,
        "error": summary,
        "error_code": "interaction_contract_invalid",
        "issues": list(issues),
        "validation_errors": [
            {
                "code": "VALIDATION_FAILED",
                "path": "/components",
                "message": str(issue),
            }
            for issue in issues
        ],
        "fix_guide": get_interaction_fix_guide(),
    }


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
    start_timeout_seconds: float = 5.0
    send_timeout_seconds: float = 1.0
    wait_ack_seconds: float = 0.3
    event_history_limit: int = 4096
    strict_component_types: bool = True


_RUNTIME_SETTINGS = MetaUIRuntimeSettings()
_ORCHESTRATOR: Optional["MetaUIOrchestrator"] = None

__all__ = [
    "MetaUIEndpoint",
    "MetaUIOrchestrator",
    "MetaUIRuntimeSettings",
    "configure_metaui_runtime",
    "get_metaui_orchestrator",
    "get_metaui_runtime_settings",
]

try:
    from websockets.server import serve  # type: ignore
except Exception:  # pragma: no cover - compatibility fallback
    try:
        from websockets.legacy.server import serve  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        serve = None


@dataclass
class _ClientConnection:
    websocket: Any
    capabilities: MetaUIClientCapabilities
    connected_at: float


@dataclass(frozen=True)
class _SendSnapshot:
    ws_url: str
    clients: Sequence[tuple[str, _ClientConnection]]


@dataclass(frozen=True)
class _PatchPreparation:
    patched_spec: MetaUISpec
    base_session_id: str
    base_state: Dict[str, Any]


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
        start_timeout_seconds: float = 5.0,
        send_timeout_seconds: float = 2.5,
        wait_ack_seconds: float = 0.9,
        event_history_limit: int = 4096,
        strict_component_types: bool = True,
        upload_store: Optional[UploadStore] = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.token = (token or "").strip() or None
        self._auto_ui = bool(auto_ui)
        self.hello_timeout_seconds = max(0.5, float(hello_timeout_seconds))
        self.start_timeout_seconds = max(0.2, float(start_timeout_seconds))
        self.send_timeout_seconds = max(0.2, float(send_timeout_seconds))
        self.wait_ack_seconds = max(0.0, float(wait_ack_seconds))
        self.event_history_limit = max(64, int(event_history_limit))
        self.strict_component_types = bool(strict_component_types)

        self._server: Any = None
        self._endpoint: Optional[MetaUIEndpoint] = None
        self._state_lock = asyncio.Lock()
        self._events_cond = asyncio.Condition()
        self._clients: Dict[str, _ClientConnection] = {}
        self._client_ready = asyncio.Event()

        self._sessions: Dict[str, MetaUISession] = {}
        self._event_store = MetaUIEventStore(limit=self.event_history_limit)

        self._ack_state_ttl_seconds = max(30.0, self.wait_ack_seconds * 20.0)
        self._ack_state_max_entries = 4096
        self._ack_tracker = _AckTracker(
            ttl_seconds=self._ack_state_ttl_seconds,
            max_entries=self._ack_state_max_entries,
        )

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

        try:
            self._server = await asyncio.wait_for(
                serve(self._handle_connection, self.host, self.port),
                timeout=self.start_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError(
                f"MetaUI orchestrator start timed out after {self.start_timeout_seconds:.2f}s."
            ) from exc
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
            for waiter in self._ack_tracker.waiters.values():
                if not waiter.future.done():
                    waiter.future.set_result(None)
            self._ack_tracker.clear()
            self._event_store.clear()

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
            phases = phase_counts(self._sessions)
            event_store_health = self._event_store.health_snapshot()
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
                "event_history_size": self._event_store.size,
                "event_store_health": event_store_health.to_dict(),
            }

    async def set_auto_ui(self, enabled: bool) -> Dict[str, Any]:
        self._auto_ui = bool(enabled)
        return {"success": True, "auto_ui": self._auto_ui}

    async def list_sessions(self) -> Dict[str, Any]:
        async with self._state_lock:
            items = list_sessions_sorted(self._sessions)
        return {"success": True, "sessions": items}

    async def get_session(self, ui_id: str) -> Dict[str, Any]:
        async with self._state_lock:
            snapshot = snapshot_session(self._sessions, ui_id=ui_id)
            if snapshot is None:
                return {"success": False, "error": f"unknown ui_id: {ui_id}"}
            return {
                "success": True,
                "session": snapshot["session"],
                "spec": snapshot["spec"],
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
        async with self._state_lock:
            selected, consumed = self._event_store.query(
                ui_id=ui_id,
                session_id=session_id,
                event_types=event_types,
                since_ts=since_ts,
                limit=limit,
                consume=consume,
            )

        return {
            "success": True,
            "events": [event.model_dump(mode="json") for event in selected],
            "count": len(selected),
            "consumed": consumed,
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
        try:
            normalized_spec = (
                spec.model_dump(mode="json")
                if isinstance(spec, MetaUISpec)
                else normalize_metaui_spec(
                    spec,
                    strict_component_types=self.strict_component_types,
                )
            )
            interaction_issues = collect_interaction_contract_issues(normalized_spec)
            if interaction_issues:
                return _interaction_contract_error_payload(
                    summary="invalid interaction contract in spec",
                    issues=interaction_issues,
                )
            validated = MetaUISpec.model_validate(normalized_spec)
        except Exception as exc:
            return {
                "success": False,
                "error": f"invalid spec: {exc}",
                "error_code": "invalid_spec",
            }
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

        result = await self._broadcast_render_full_session(session=session, expect_ack=False)

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
        normalized_patch = normalize_metaui_patch(
            patch,
            strict_component_types=self.strict_component_types,
        )
        preparation, preparation_error = await self._prepare_patch(
            ui_id=ui_id,
            normalized_patch=normalized_patch,
        )
        if preparation_error is not None:
            return preparation_error
        if preparation is None:
            return {"success": False, "error": "patch preparation failed unexpectedly."}

        render_session = MetaUISession(
            ui_id=ui_id,
            session_id=preparation.base_session_id if session_id is None else session_id,
            spec=preparation.patched_spec,
            state=preparation.base_state,
            phase=MetaUIPhase.RENDERING,
        )
        result = await self._broadcast_render_full_session(session=render_session, expect_ack=False)
        return await self._commit_patch_result(
            ui_id=ui_id,
            result=result,
            patched_spec=preparation.patched_spec,
        )

    async def _prepare_patch(
        self,
        *,
        ui_id: str,
        normalized_patch: Dict[str, Any],
    ) -> tuple[Optional[_PatchPreparation], Optional[Dict[str, Any]]]:
        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session is None:
                return None, {"success": False, "error": f"unknown ui_id: {ui_id}"}
            try:
                patched_dict = apply_structural_patch_to_spec(
                    session.spec.model_dump(mode="json"),
                    normalized_patch,
                )
                patched_dict = normalize_metaui_spec(
                    patched_dict,
                    strict_component_types=self.strict_component_types,
                )
                interaction_issues = collect_interaction_contract_issues(patched_dict)
                if interaction_issues:
                    return None, _interaction_contract_error_payload(
                        summary="invalid interaction contract in patch result",
                        issues=interaction_issues,
                    )
                patched_spec = MetaUISpec.model_validate(patched_dict)
            except Exception as exc:
                return None, {"success": False, "error": f"invalid patch: {exc}"}
            session.update_phase(MetaUIPhase.RENDERING)
            session.bump_version()
            preparation = _PatchPreparation(
                patched_spec=patched_spec,
                base_session_id=session.session_id,
                base_state=deepcopy(session.state),
            )
            return preparation, None

    async def _commit_patch_result(
        self,
        *,
        ui_id: str,
        result: Dict[str, Any],
        patched_spec: MetaUISpec,
    ) -> Dict[str, Any]:
        committed_result = result
        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session is None:
                return committed_result
            can_commit = bool(committed_result.get("success")) or str(committed_result.get("error") or "") == ERROR_NO_CONNECTED_CLIENTS
            if can_commit:
                session.spec = patched_spec
                session.update_phase(MetaUIPhase.INTERACTIVE)
                if not committed_result.get("success"):
                    committed_result = dict(committed_result)
                    committed_result["spec_synced_for_replay"] = True
            else:
                session.update_phase(MetaUIPhase.RECOVERING, error=committed_result.get("error"))
        return committed_result

    async def set_state(
        self,
        *,
        ui_id: str,
        state: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(state, Mapping):
            return {"success": False, "error": "`state` must be a JSON object."}
        state_patch = deepcopy(dict(state))
        async with self._state_lock:
            session = self._sessions.get(ui_id)
            if session is None:
                return {"success": False, "error": f"unknown ui_id: {ui_id}"}
            session.state = merge_nested_dicts(session.state, state_patch)
            session.bump_version()
        return await self._broadcast_state_update(
            ui_id=ui_id,
            session_id=session_id,
            state_patch=state_patch,
        )

    async def notify(
        self,
        *,
        ui_id: Optional[str],
        message: str,
        level: str = "info",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        _ = (ui_id, message, level, session_id)
        return {
            "success": False,
            "error": "notify is not available in strict A2UI transport mode.",
            "error_code": "unsupported_operation",
        }

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
        snapshot = await self._prepare_send_snapshot()
        payload = command.model_dump(mode="json")
        payloads_by_client = {
            client_id: (payload,)
            for client_id, _ in snapshot.clients
        }
        return await self._send_payloads_to_clients(
            payloads_by_client=payloads_by_client,
            command_id=command.command_id,
            ui_id=command.ui_id,
            session_id=command.session_id,
            expect_ack=expect_ack,
            snapshot=snapshot,
        )

    async def _await_ack(self, *, command_id: str, sent: int, expect_ack: bool) -> int:
        ack_count = self._ack_count(command_id)
        if not expect_ack or sent <= 0 or self.wait_ack_seconds <= 0:
            return ack_count

        waiter = _AckWaiter(
            expected=1,
            future=asyncio.get_running_loop().create_future(),
        )
        async with self._state_lock:
            self._ack_tracker.waiters[command_id] = waiter
        try:
            await asyncio.wait_for(waiter.future, timeout=self.wait_ack_seconds)
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            # Gracefully degrade when waiter is cancelled by shutdown/race.
            return self._ack_count(command_id)
        finally:
            async with self._state_lock:
                self._ack_tracker.waiters.pop(command_id, None)
        return self._ack_count(command_id)

    async def _send_payload_batch(
        self,
        *,
        connection: _ClientConnection,
        payloads: Sequence[Dict[str, Any]],
    ) -> bool:
        for payload in payloads:
            await asyncio.wait_for(
                connection.websocket.send(json.dumps(payload, ensure_ascii=False)),
                timeout=self.send_timeout_seconds,
            )
        return any(
            isinstance(payload, dict) and payload.get("command_id")
            for payload in payloads
        )

    async def _remove_stale_clients(self, client_ids: Sequence[str]) -> None:
        if not client_ids:
            return
        async with self._state_lock:
            for client_id in client_ids:
                self._clients.pop(client_id, None)
            if not self._clients:
                self._client_ready.clear()

    async def _send_payloads_to_clients(
        self,
        *,
        payloads_by_client: Dict[str, Sequence[Dict[str, Any]]],
        command_id: str,
        ui_id: Optional[str],
        session_id: Optional[str],
        expect_ack: bool,
        snapshot: _SendSnapshot,
    ) -> Dict[str, Any]:
        clients = list(snapshot.clients)

        if not clients:
            return self._build_delivery_result(
                command_id=command_id,
                ui_id=ui_id,
                session_id=session_id,
                ws_url=snapshot.ws_url,
                sent=0,
                ack_sent=0,
                connected_clients=0,
                ack_count=0,
                expect_ack=expect_ack,
            )

        sent = 0
        ack_sent = 0
        stale_clients: list[str] = []
        for client_id, connection in clients:
            payloads = payloads_by_client.get(client_id) or ()
            if not payloads:
                continue
            try:
                has_command_payload = await self._send_payload_batch(
                    connection=connection,
                    payloads=payloads,
                )
                sent += 1
                if has_command_payload:
                    ack_sent += 1
            except Exception as exc:  # pragma: no cover - transport edge
                logger.debug("MetaUI send failed (%s): %s", client_id, exc)
                stale_clients.append(client_id)

        await self._remove_stale_clients(stale_clients)

        ack_count = await self._await_ack(
            command_id=command_id,
            sent=ack_sent,
            expect_ack=expect_ack,
        )
        return self._build_delivery_result(
            command_id=command_id,
            ui_id=ui_id,
            session_id=session_id,
            ws_url=snapshot.ws_url,
            sent=sent,
            ack_sent=ack_sent,
            connected_clients=len(clients) - len(stale_clients),
            ack_count=ack_count,
            expect_ack=expect_ack,
        )

    async def _prepare_send_snapshot(self) -> _SendSnapshot:
        endpoint = await self.ensure_started()
        async with self._state_lock:
            self._prune_ack_state(now=asyncio.get_running_loop().time())
            clients = list(self._clients.items())
        return _SendSnapshot(
            ws_url=endpoint.ws_url,
            clients=clients,
        )

    def _build_delivery_result(
        self,
        *,
        command_id: str,
        ui_id: Optional[str],
        session_id: Optional[str],
        ws_url: str,
        sent: int,
        ack_sent: int,
        connected_clients: int,
        ack_count: int,
        expect_ack: bool,
    ) -> Dict[str, Any]:
        ack_required = bool(expect_ack and ack_sent > 0 and self.wait_ack_seconds > 0)
        ack_satisfied = (not ack_required) or ack_count > 0
        success = sent > 0 and ack_satisfied
        result: Dict[str, Any] = {
            "success": success,
            "command_id": command_id,
            "ui_id": ui_id,
            "session_id": session_id,
            "ws_url": ws_url,
            "sent": sent,
            "ack_sent": ack_sent,
            "connected_clients": connected_clients,
            "acks": ack_count,
            "ack_required": ack_required,
        }
        if sent <= 0:
            result["error"] = ERROR_NO_CONNECTED_CLIENTS
        elif ack_required and ack_count <= 0:
            result["error"] = ERROR_ACK_TIMEOUT
        return result

    def _build_render_payloads_for_client(
        self,
        *,
        connection: _ClientConnection,
        session: MetaUISession,
        command_id: str,
        include_state: bool,
    ) -> Sequence[Dict[str, Any]]:
        _ = (connection, command_id)
        return build_ui_render_sequence(
            spec=session.spec,
            state=session.state if include_state and session.state else None,
            catalog_id=build_catalog_snapshot(get_component_catalog())["catalogId"],
        )

    async def _broadcast_render_full_session(
        self,
        *,
        session: MetaUISession,
        expect_ack: bool,
    ) -> Dict[str, Any]:
        command_id = new_command_id()
        snapshot = await self._prepare_send_snapshot()
        clients = dict(snapshot.clients)
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
            snapshot=snapshot,
        )

    async def _broadcast_state_update(
        self,
        *,
        ui_id: str,
        session_id: Optional[str],
        state_patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        command_id = new_command_id()
        snapshot = await self._prepare_send_snapshot()
        clients = dict(snapshot.clients)

        payloads_by_client: Dict[str, Sequence[Dict[str, Any]]] = {}
        for client_id, connection in clients.items():
            if not connection.capabilities.supports_feature("a2ui_stream_v1"):
                continue
            payloads_by_client[client_id] = (
                build_data_model_update_message(
                    surface_id=ui_id,
                    state_patch=state_patch,
                    path="/",
                ),
            )

        return await self._send_payloads_to_clients(
            payloads_by_client=payloads_by_client,
            command_id=command_id,
            ui_id=ui_id,
            session_id=session_id,
            expect_ack=False,
            snapshot=snapshot,
        )

    async def _broadcast_close(
        self,
        *,
        ui_id: str,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        command_id = new_command_id()
        snapshot = await self._prepare_send_snapshot()
        clients = dict(snapshot.clients)

        payloads_by_client: Dict[str, Sequence[Dict[str, Any]]] = {}
        for client_id, connection in clients.items():
            if not connection.capabilities.supports_feature("a2ui_stream_v1"):
                continue
            payloads_by_client[client_id] = (build_delete_surface_message(surface_id=ui_id),)

        return await self._send_payloads_to_clients(
            payloads_by_client=payloads_by_client,
            command_id=command_id,
            ui_id=ui_id,
            session_id=session_id,
            expect_ack=False,
            snapshot=snapshot,
        )

    async def _register_client(
        self,
        *,
        client_id: str,
        connection: _ClientConnection,
    ) -> None:
        async with self._state_lock:
            self._clients[client_id] = connection
            self._client_ready.set()

    async def _unregister_client(self, client_id: str) -> None:
        async with self._state_lock:
            self._clients.pop(client_id, None)
            if not self._clients:
                self._client_ready.clear()

    async def _accept_client_connection(
        self,
        *,
        websocket: Any,
    ) -> tuple[Optional[str], Optional[_ClientConnection], Optional[HelloAck]]:
        raw_hello = await self._recv_json(websocket, timeout=self.hello_timeout_seconds)
        if not isinstance(raw_hello, dict) or raw_hello.get("type") != "hello":
            await websocket.close(code=1008, reason="missing hello")
            return None, None, None

        try:
            hello = ClientHello.model_validate(raw_hello)
        except Exception:
            await websocket.close(code=1008, reason="invalid hello payload")
            return None, None, None

        if self.token and hello.token != self.token:
            await websocket.close(code=4401, reason="unauthorized")
            return None, None, None

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
        hello_ack = HelloAck(
            client_id=client_id,
            protocol=negotiated.protocol_version,
            auto_ui=self._auto_ui,
            active_sessions=len(self._sessions),
            catalog=CatalogSnapshot.model_validate(build_catalog_snapshot(catalog)),
            negotiated_features=negotiated.features,
        )
        return client_id, connection, hello_ack

    async def _consume_client_messages(self, *, websocket: Any) -> None:
        async for raw in websocket:
            message = self._decode_json(raw)
            if not isinstance(message, dict):
                continue
            translated_event = translate_client_event_message(message)
            if translated_event is not None:
                await self._record_event(translated_event)
                continue
            if message.get("type") == "event":
                await self._record_event(message)

    async def _handle_connection(self, websocket: Any, path: Optional[str] = None) -> None:
        if path and path not in {"/", "/metaui"}:
            await websocket.close(code=1008, reason="unsupported path")
            return

        client_id, connection, hello_ack = await self._accept_client_connection(
            websocket=websocket,
        )
        if client_id is None or connection is None or hello_ack is None:
            return

        await self._register_client(client_id=client_id, connection=connection)

        await websocket.send(
            json.dumps(hello_ack.model_dump(mode="json"), ensure_ascii=False)
        )
        await self._replay_sessions_to_client(connection)

        try:
            await self._consume_client_messages(websocket=websocket)
        finally:
            await self._unregister_client(client_id)

    async def _replay_sessions_to_client(self, connection: _ClientConnection) -> None:
        async with self._state_lock:
            sessions = list(self._sessions.values())
        if not sessions:
            return

        sessions.sort(key=lambda item: float(item.updated_at))
        for session in sessions:
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
                await self._record_event(
                    {
                        "ui_id": session.ui_id,
                        "session_id": session.session_id,
                        "event_type": "error",
                        "payload": {
                            "code": "REPLAY_SEND_FAILED",
                            "message": f"Replay failed for UI '{session.ui_id}': {exc}",
                            "stage": "replay",
                        },
                        "metadata": {"source": "metaui_orchestrator"},
                    }
                )
                return

    async def _record_ack(self, command_id: str) -> None:
        if not command_id:
            return
        async with self._state_lock:
            now = asyncio.get_running_loop().time()
            self._ack_tracker.record(command_id, now=now)

    def _ack_count(self, command_id: str) -> int:
        return self._ack_tracker.count(command_id)

    def _prune_ack_state(self, *, now: Optional[float] = None) -> None:
        if now is None:
            now = asyncio.get_running_loop().time()
        self._ack_tracker.prune(now=now)

    async def _record_event(self, event_payload: Dict[str, Any]) -> None:
        try:
            event = MetaUIEvent.model_validate(event_payload)
        except Exception:
            return

        if not await self._accept_event_id(event.event_id):
            return

        validation_component, validation_state = await self._event_validation_context(event)
        persist_event_uploads(event, upload_store=self._upload_store)
        sanitize_event_payload_in_place(event)
        validation_errors = event_validation_errors(
            event=event,
            validation_component=validation_component,
            validation_state=validation_state,
        )
        await self._append_event_and_update_phase(event=event, validation_errors=validation_errors)

        async with self._events_cond:
            self._events_cond.notify_all()

    async def _accept_event_id(self, event_id: str) -> bool:
        async with self._state_lock:
            return self._event_store.accept_event_id(event_id)

    async def _event_validation_context(
        self,
        event: MetaUIEvent,
    ) -> tuple[Optional[Mapping[str, Any]], Dict[str, Any]]:
        validation_component: Optional[Mapping[str, Any]] = None
        validation_state: Dict[str, Any] = {}
        async with self._state_lock:
            session_for_validation = self._sessions.get(event.ui_id)
            if not session_for_validation:
                return validation_component, validation_state
            component = find_validation_component(
                spec=session_for_validation.spec,
                component_id=event.component_id or "",
            )
            if component is not None:
                validation_component = component
                if isinstance(session_for_validation.state, Mapping):
                    validation_state = deepcopy(dict(session_for_validation.state))
        return validation_component, validation_state

    async def _append_event_and_update_phase(
        self,
        *,
        event: MetaUIEvent,
        validation_errors: Sequence[str],
    ) -> None:
        async with self._state_lock:
            if validation_errors:
                event.event_type = "error"
                event.payload = dict(event.payload)
                event.payload["code"] = "VALIDATION_FAILED"
                event.payload["validation_errors"] = list(validation_errors)

            session = self._sessions.get(event.ui_id)
            if session and session.session_id and event.session_id and session.session_id != event.session_id:
                session = None
            self._event_store.append(event)
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


def configure_metaui_runtime(config_dict: dict[str, Any]) -> None:
    """Configure process-wide MetaUI runtime defaults from AEIVA config."""
    global _RUNTIME_SETTINGS, _ORCHESTRATOR

    block = config_dict.get("metaui_config")
    if not isinstance(block, dict):
        return

    token = block.get("token")
    token_env_var = str(block.get("token_env_var") or "").strip()
    if not token and token_env_var:
        token = os.getenv(token_env_var)

    _RUNTIME_SETTINGS = replace(
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
        start_timeout_seconds=_normalize_float(
            block.get("start_timeout_seconds"),
            _RUNTIME_SETTINGS.start_timeout_seconds,
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
        strict_component_types=bool(
            block.get("strict_component_types", _RUNTIME_SETTINGS.strict_component_types)
        ),
    )
    _ORCHESTRATOR = None


def get_metaui_runtime_settings() -> MetaUIRuntimeSettings:
    return _RUNTIME_SETTINGS


def get_metaui_orchestrator(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    token: Optional[str] = None,
    strict_component_types: Optional[bool] = None,
) -> MetaUIOrchestrator:
    global _ORCHESTRATOR

    settings = _RUNTIME_SETTINGS
    resolved_host = host or settings.host
    resolved_port = settings.port if port is None else int(port)
    resolved_token = token if token is not None else settings.token
    resolved_strict = (
        settings.strict_component_types
        if strict_component_types is None
        else bool(strict_component_types)
    )

    if _ORCHESTRATOR is not None:
        same_endpoint = (
            _ORCHESTRATOR.host == resolved_host
            and _ORCHESTRATOR.port == resolved_port
            and _ORCHESTRATOR.token == ((resolved_token or "").strip() or None)
            and _ORCHESTRATOR.strict_component_types == resolved_strict
        )
        if same_endpoint:
            return _ORCHESTRATOR

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
        start_timeout_seconds=settings.start_timeout_seconds,
        send_timeout_seconds=settings.send_timeout_seconds,
        wait_ack_seconds=settings.wait_ack_seconds,
        event_history_limit=settings.event_history_limit,
        strict_component_types=resolved_strict,
        upload_store=upload_store,
    )
    return _ORCHESTRATOR
