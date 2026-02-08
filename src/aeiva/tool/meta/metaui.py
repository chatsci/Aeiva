"""
MetaUI Tool: channel-agnostic desktop UI orchestration.
"""

from __future__ import annotations

import atexit
import asyncio
import os
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from aeiva.metaui.desktop_runtime import resolve_desktop_python
from aeiva.metaui.spec_normalizer import normalize_metaui_spec
from aeiva.metaui.component_catalog import get_component_catalog
from aeiva.metaui.a2ui_protocol import get_protocol_schema_bundle
from aeiva.metaui.message_evaluator import evaluate_server_messages
from aeiva.metaui.orchestrator import (
    get_metaui_orchestrator,
    get_metaui_runtime_settings,
)
from aeiva.metaui.protocol import MetaUISpec
from aeiva.metaui.intent_spec import build_intent_spec
from aeiva.metaui.session import MetaUIPhase
from aeiva.metaui.update_strategy import (
    apply_structural_patch_to_spec,
    decide_patch_routing,
)

from ..capability import Capability
from ..decorator import tool


_DESKTOP_LAUNCH_COOLDOWN_SECONDS = 8.0
_DESKTOP_CONNECT_GRACE_SECONDS = 45.0
_DESKTOP_PENDING_ENV_VAR = "AEIVA_METAUI_DESKTOP_PENDING_UNTIL_MONO"
_desktop_launch_lock = threading.Lock()
_last_desktop_launch_attempt_mono = 0.0
_desktop_connect_grace_until_mono = 0.0
_LAUNCHED_DESKTOP_PROCESSES: List[subprocess.Popen] = []
_KNOWN_OPERATIONS = (
    "start, status, compose, validate_spec, catalog, protocol_schema, validate_messages, "
    "launch_desktop, render_full, scaffold, patch, set_state, notify, close, "
    "set_auto_ui, list_sessions, get_session, update_phase, poll_events, wait_event"
)
_VALID_OPERATION_KEYS = {
    "start",
    "status",
    "compose",
    "validate_spec",
    "catalog",
    "protocol_schema",
    "validate_messages",
    "launch_desktop",
    "render_full",
    "scaffold",
    "patch",
    "set_state",
    "notify",
    "close",
    "set_auto_ui",
    "list_sessions",
    "get_session",
    "update_phase",
    "poll_events",
    "wait_event",
}


def _mark_desktop_connect_pending() -> None:
    global _desktop_connect_grace_until_mono
    grace_until = time.monotonic() + _DESKTOP_CONNECT_GRACE_SECONDS
    with _desktop_launch_lock:
        _desktop_connect_grace_until_mono = grace_until
    os.environ[_DESKTOP_PENDING_ENV_VAR] = f"{grace_until:.6f}"


def _clear_desktop_connect_pending() -> None:
    global _desktop_connect_grace_until_mono
    with _desktop_launch_lock:
        _desktop_connect_grace_until_mono = 0.0
    os.environ.pop(_DESKTOP_PENDING_ENV_VAR, None)


def _is_external_desktop_pending() -> bool:
    raw = os.getenv(_DESKTOP_PENDING_ENV_VAR)
    if not raw:
        return False
    try:
        pending_until = float(raw)
    except Exception:
        return False
    return time.monotonic() < pending_until


def _try_claim_desktop_launch_slot() -> bool:
    global _last_desktop_launch_attempt_mono
    with _desktop_launch_lock:
        now = time.monotonic()
        elapsed = now - _last_desktop_launch_attempt_mono
        in_grace_period = now < _desktop_connect_grace_until_mono
        if _is_external_desktop_pending():
            return False
        if elapsed < _DESKTOP_LAUNCH_COOLDOWN_SECONDS or in_grace_period:
            return False
        _last_desktop_launch_attempt_mono = now
        return True


def _register_launched_desktop_process(process: subprocess.Popen) -> None:
    with _desktop_launch_lock:
        _LAUNCHED_DESKTOP_PROCESSES.append(process)


def _prune_dead_desktop_processes() -> None:
    with _desktop_launch_lock:
        alive: List[subprocess.Popen] = []
        for process in _LAUNCHED_DESKTOP_PROCESSES:
            try:
                if process.poll() is None:
                    alive.append(process)
            except Exception:
                continue
        _LAUNCHED_DESKTOP_PROCESSES[:] = alive


def _get_live_desktop_process() -> Optional[subprocess.Popen]:
    _prune_dead_desktop_processes()
    with _desktop_launch_lock:
        if not _LAUNCHED_DESKTOP_PROCESSES:
            return None
        return _LAUNCHED_DESKTOP_PROCESSES[-1]


def _cleanup_launched_desktops() -> None:
    with _desktop_launch_lock:
        processes = list(_LAUNCHED_DESKTOP_PROCESSES)
        _LAUNCHED_DESKTOP_PROCESSES.clear()
    for process in processes:
        try:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
                process.wait(timeout=2)
            except Exception:
                pass


atexit.register(_cleanup_launched_desktops)


def _reset_desktop_launch_state_for_tests() -> None:
    global _last_desktop_launch_attempt_mono, _desktop_connect_grace_until_mono
    with _desktop_launch_lock:
        _last_desktop_launch_attempt_mono = 0.0
        _desktop_connect_grace_until_mono = 0.0
        _LAUNCHED_DESKTOP_PROCESSES.clear()
    os.environ.pop(_DESKTOP_PENDING_ENV_VAR, None)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _soften_no_clients_result(result: Dict[str, Any], *, operation: str) -> Dict[str, Any]:
    if result.get("success") is True:
        return result
    if str(result.get("error") or "") != "no_connected_clients":
        return result
    softened = dict(result)
    softened["success"] = True
    softened["pending_client_connection"] = True
    softened.pop("ws_url", None)
    softened["warning"] = (
        f"{operation} queued; UI will render when desktop client connects."
    )
    return softened


def _merge_scaffold_overrides(
    base_spec: Dict[str, Any],
    override_spec: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Merge user-provided scaffold overrides.

    High-level keys (title/actions/state_bindings) are always allowed.
    Structural overrides (components/root) are intentionally ignored to keep
    scaffold intent-driven and prevent stale template carry-over.
    """
    merged = dict(base_spec)
    diagnostics: Dict[str, Any] = {
        "override_provided": bool(isinstance(override_spec, dict)),
        "structural_override_requested": False,
        "structural_override_applied": False,
    }
    if not isinstance(override_spec, dict):
        return merged, diagnostics

    title = override_spec.get("title")
    if isinstance(title, str) and title.strip():
        merged["title"] = title.strip()

    actions = override_spec.get("actions")
    if isinstance(actions, list):
        merged["actions"] = actions

    bindings = override_spec.get("state_bindings")
    if isinstance(bindings, dict):
        merged["state_bindings"] = bindings

    components = override_spec.get("components")
    root = override_spec.get("root")
    has_components_override = isinstance(components, list)
    has_root_override = isinstance(root, list)
    structural_override = bool(has_components_override or has_root_override)

    diagnostics["structural_override_requested"] = structural_override
    if structural_override:
        diagnostics["structural_override_applied"] = False
        diagnostics["warning"] = (
            "Ignored scaffold structural override. Use render_full for structural UI changes."
        )
    return merged, diagnostics


async def _resolve_target_ui_id(
    orchestrator: Any,
    *,
    ui_id: Optional[str],
    session_id: Optional[str],
) -> Optional[str]:
    if isinstance(ui_id, str) and ui_id.strip():
        return ui_id.strip()

    sessions_resp = await orchestrator.list_sessions()
    if not sessions_resp.get("success"):
        return None

    sessions = sessions_resp.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        return None

    candidates = sessions
    if isinstance(session_id, str) and session_id.strip():
        sid = session_id.strip()
        filtered = [item for item in sessions if isinstance(item, dict) and item.get("session_id") == sid]
        if filtered:
            candidates = filtered

    for item in candidates:
        if isinstance(item, dict):
            cid = item.get("ui_id")
            if isinstance(cid, str) and cid.strip():
                return cid.strip()
    return None


def _try_launch_desktop(ws_url: str, token: Optional[str]) -> Dict[str, Any]:
    python_exec = resolve_desktop_python(current_executable=sys.executable)
    if not python_exec:
        return {
            "success": False,
            "error": (
                "MetaUI desktop runtime unavailable: no Python interpreter with "
                "PySide6 + QtWebEngine found. Install desktop dependencies with "
                "`uv sync --extra metaui` (or `pip install -e '.[metaui]'`), then "
                "run gateway with that environment."
            ),
        }

    cmd = [python_exec, "-m", "aeiva.metaui.desktop_client", "--ws-url", ws_url]
    if token:
        cmd.extend(["--token", token])
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        _register_launched_desktop_process(process)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "pid": process.pid}


@tool(
    description=(
        "Render and manage desktop MetaUI sessions via local websocket. "
        f"Operations: {_KNOWN_OPERATIONS}. "
        "Primary path (A2UI-style): use `catalog` to inspect supported components, then send explicit `spec` via "
        "`render_full`, and use `set_state`/`patch` for incremental updates. "
        "For scaffold: pass natural-language `intent` only as compatibility fallback."
    ),
    capabilities=[Capability.NETWORK, Capability.PROCESS],
)
async def metaui(
    operation: str,
    *,
    spec: Optional[Dict[str, Any]] = None,
    patch: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, Any]] = None,
    ui_id: Optional[str] = None,
    session_id: Optional[str] = None,
    message: Optional[str] = None,
    level: str = "info",
    auto_ui: Optional[bool] = None,
    phase: Optional[str] = None,
    error: Optional[str] = None,
    intent: Optional[str] = None,
    ensure_visible: bool = True,
    wait_for_client_seconds: float = 1.0,
    wait_timeout_seconds: float = 30.0,
    limit: int = 50,
    consume: bool = False,
    event_types: Optional[List[str]] = None,
    since_ts: Optional[float] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    token: Optional[str] = None,
    auto_route_structural_patch: bool = True,
) -> Dict[str, Any]:
    """
    MetaUI desktop operations.

    Args:
        operation: The operation to perform (e.g. compose, scaffold, render_full, patch, set_state, status).
        intent: For scaffold — the user's natural-language UI request. This drives
            dynamic composition for common workspace patterns.
        spec: Full MetaUI spec dict for render_full, or override dict for scaffold.
        patch: Patch payload for the patch operation.
        state: State dict for set_state.
        ui_id: Target UI session identifier.
        session_id: Logical session grouping key.
        message: Notification message for notify operation.
        level: Notification severity (info, warn, error).
        phase: Target phase for update_phase.
        ensure_visible: Auto-launch desktop window if no client is connected.
    """
    try:
        operation_key = (operation or "").strip().lower()
        if operation_key not in _VALID_OPERATION_KEYS:
            return {
                "success": False,
                "error": (
                    f"Unknown operation: {operation}. "
                    f"Valid operations: {_KNOWN_OPERATIONS}."
                ),
            }

        if operation_key == "compose":
            composed = build_intent_spec(intent or "", session_id=session_id)
            diagnostics: Dict[str, Any] = {}
            if spec and isinstance(spec, dict):
                composed, diagnostics = _merge_scaffold_overrides(composed, spec)
            try:
                normalized = MetaUISpec.model_validate(normalize_metaui_spec(composed)).model_dump(mode="json")
            except Exception as exc:
                return {"success": False, "error": f"invalid composed spec: {exc}"}
            response: Dict[str, Any] = {"success": True, "spec": normalized, "session_id": session_id}
            if diagnostics:
                response["diagnostics"] = diagnostics
                warning = diagnostics.get("warning")
                if warning:
                    response["warning"] = warning
            return response

        if operation_key == "validate_spec":
            if spec is None:
                return {"success": False, "error": "`spec` is required for validate_spec."}
            try:
                normalized = MetaUISpec.model_validate(
                    normalize_metaui_spec(spec, strict_component_types=True)
                ).model_dump(mode="json")
            except Exception as exc:
                return {"success": False, "error": f"invalid spec: {exc}"}
            return {"success": True, "spec": normalized}

        if operation_key == "catalog":
            return {
                "success": True,
                "catalog": get_component_catalog(),
                "recommended_flow": [
                    "1) call metaui.catalog",
                    "2) build explicit MetaUI spec in model output",
                    "3) call metaui.render_full(spec=...)",
                    "4) call metaui.set_state / metaui.patch for updates",
                ],
            }

        if operation_key == "protocol_schema":
            return {
                "success": True,
                "schema": get_protocol_schema_bundle(),
                "catalog": get_component_catalog(),
            }

        if operation_key == "validate_messages":
            messages: Any = None
            if isinstance(spec, dict):
                messages = spec.get("messages")
            elif isinstance(spec, list):
                messages = spec
            if not isinstance(messages, list):
                return {
                    "success": False,
                    "error": "`spec.messages` (array) is required for validate_messages.",
                }
            evaluation = evaluate_server_messages(messages)
            return {"success": True, "evaluation": evaluation}

        settings = get_metaui_runtime_settings()
        if not settings.enabled:
            return {"success": False, "error": "metaui is disabled by configuration"}

        resolved_host = host or settings.host or os.getenv("AEIVA_METAUI_HOST", "127.0.0.1")
        resolved_port = _as_int(
            port,
            _as_int(settings.port, _as_int(os.getenv("AEIVA_METAUI_PORT", "8765"), 8765)),
        )
        resolved_token = token if token is not None else (settings.token or os.getenv("AEIVA_METAUI_TOKEN"))

        orchestrator = get_metaui_orchestrator(
            host=resolved_host,
            port=resolved_port,
            token=resolved_token,
        )
        endpoint = await orchestrator.ensure_started()
        if operation_key == "start":
            return {
                "success": True,
                "running": True,
                "ws_url": endpoint.ws_url,
                "host": endpoint.host,
                "port": endpoint.port,
                "token_required": endpoint.token_required,
            }

        if operation_key == "status":
            return await orchestrator.status()

        if operation_key == "set_auto_ui":
            if auto_ui is None:
                return {"success": False, "error": "`auto_ui` is required for set_auto_ui."}
            return await orchestrator.set_auto_ui(auto_ui)

        if operation_key == "launch_desktop":
            existing = _get_live_desktop_process()
            if existing is not None:
                result = {"success": True, "pid": existing.pid, "reused_existing_window": True}
                connected = await orchestrator.wait_for_client(timeout=wait_for_client_seconds)
                result["client_connected"] = connected
                if connected:
                    _clear_desktop_connect_pending()
                else:
                    _mark_desktop_connect_pending()
            else:
                if not _try_claim_desktop_launch_slot():
                    return {
                        "success": True,
                        "pending_client_connection": True,
                        "warning": "Desktop launch is in cooldown/grace period; reusing pending launch window.",
                        "ws_url": endpoint.ws_url,
                    }
                launch = await asyncio.to_thread(_try_launch_desktop, endpoint.ws_url, resolved_token)
                result = dict(launch)
                if result.get("success"):
                    connected = await orchestrator.wait_for_client(timeout=wait_for_client_seconds)
                    result["client_connected"] = connected
                    if connected:
                        _clear_desktop_connect_pending()
                    else:
                        _mark_desktop_connect_pending()
                else:
                    _clear_desktop_connect_pending()
            result["ws_url"] = endpoint.ws_url
            return result

        desktop_pending_connection = False
        if ensure_visible:
            status = await orchestrator.status()
            auto_enabled = bool(status.get("auto_ui", True))
            if auto_enabled and int(status.get("connected_clients") or 0) <= 0:
                existing = _get_live_desktop_process()
                if existing is not None:
                    connected = await orchestrator.wait_for_client(timeout=min(wait_for_client_seconds, 0.3))
                    if not connected:
                        _mark_desktop_connect_pending()
                        desktop_pending_connection = True
                    else:
                        _clear_desktop_connect_pending()
                elif _try_claim_desktop_launch_slot():
                    launch = await asyncio.to_thread(_try_launch_desktop, endpoint.ws_url, resolved_token)
                    if not launch.get("success"):
                        _clear_desktop_connect_pending()
                        return {
                            "success": False,
                            "error": launch.get("error") or "failed to launch MetaUI desktop",
                            "ws_url": endpoint.ws_url,
                        }
                    connected = await orchestrator.wait_for_client(timeout=wait_for_client_seconds)
                    if not connected:
                        _mark_desktop_connect_pending()
                        desktop_pending_connection = True
                    else:
                        _clear_desktop_connect_pending()
                else:
                    _mark_desktop_connect_pending()
                    desktop_pending_connection = True

        if operation_key == "scaffold":
            scaffold_spec = build_intent_spec(intent or "", session_id=session_id)
            diagnostics: Dict[str, Any] = {}
            if spec and isinstance(spec, dict):
                scaffold_spec, diagnostics = _merge_scaffold_overrides(scaffold_spec, spec)
            resolved_ui_id = await _resolve_target_ui_id(
                orchestrator,
                ui_id=ui_id,
                session_id=session_id,
            )
            result = await orchestrator.render_full(
                spec=scaffold_spec,
                session_id=session_id,
                ui_id=resolved_ui_id,
            )
            softened = _soften_no_clients_result(result, operation="scaffold")
            if resolved_ui_id and resolved_ui_id != ui_id:
                softened["resolved_ui_id"] = resolved_ui_id
            if diagnostics:
                softened["diagnostics"] = diagnostics
                warning = diagnostics.get("warning")
                if warning:
                    softened["warning"] = warning
            softened["scaffold_fallback_used"] = True
            softened.setdefault(
                "warning",
                "Scaffold is compatibility fallback. Prefer catalog + render_full for deterministic A2UI-style control.",
            )
            if desktop_pending_connection:
                softened.setdefault(
                    "warning",
                    "Desktop client is still connecting; command queued and will render when ready.",
                )
                softened["pending_client_connection"] = True
            return softened

        if operation_key == "render_full":
            if spec is None:
                return {"success": False, "error": "`spec` is required for render_full."}
            result = await orchestrator.render_full(spec=spec, session_id=session_id, ui_id=ui_id)
            softened = _soften_no_clients_result(result, operation="render_full")
            if desktop_pending_connection:
                softened.setdefault(
                    "warning",
                    "Desktop client is still connecting; command queued and will render when ready.",
                )
                softened["pending_client_connection"] = True
            return softened

        if operation_key == "patch":
            resolved_ui_id = await _resolve_target_ui_id(
                orchestrator,
                ui_id=ui_id,
                session_id=session_id,
            )
            if not resolved_ui_id:
                return {"success": False, "error": "`ui_id` is required for patch (no active UI session found)."}
            if patch is None:
                return {"success": False, "error": "`patch` is required for patch."}
            routing = decide_patch_routing(patch)
            if routing.route_to_render_full:
                if not auto_route_structural_patch:
                    error_payload = {
                        "success": False,
                        "error": (
                            "Structural UI intent detected in patch payload. "
                            "Use `metaui.render_full` with an explicit spec for layout/view changes."
                        ),
                        "error_code": "structural_patch_requires_render_full",
                        "resolved_ui_id": resolved_ui_id,
                        "routing_reason": routing.reason,
                        "recommended_flow": [
                            "1) call metaui.catalog",
                            "2) build explicit MetaUI spec for the target UI",
                            "3) call metaui.render_full(spec=..., ui_id=...)",
                            "4) use metaui.patch/set_state only for non-structural updates",
                        ],
                    }
                    if routing.intent_text:
                        error_payload["detected_intent"] = routing.intent_text
                    return error_payload

                rendered_spec: Optional[Dict[str, Any]] = None
                session_snapshot = await orchestrator.get_session(resolved_ui_id)
                if session_snapshot.get("success") and isinstance(session_snapshot.get("spec"), dict):
                    rendered_spec = apply_structural_patch_to_spec(session_snapshot["spec"], patch)

                if rendered_spec is None and routing.intent_text:
                    rendered_spec = build_intent_spec(routing.intent_text, session_id=session_id)

                if rendered_spec is None:
                    return {
                        "success": False,
                        "error": "Unable to derive full spec from structural patch. Provide explicit spec to render_full.",
                        "error_code": "structural_patch_requires_render_full",
                        "resolved_ui_id": resolved_ui_id,
                        "routing_reason": routing.reason,
                    }

                result = await orchestrator.render_full(
                    spec=rendered_spec,
                    session_id=session_id,
                    ui_id=resolved_ui_id,
                )
                softened = _soften_no_clients_result(result, operation="render_full")
                if resolved_ui_id != ui_id:
                    softened["resolved_ui_id"] = resolved_ui_id
                softened["auto_routed"] = True
                softened["routed_operation"] = "render_full"
                softened["routing_reason"] = routing.reason
                if routing.intent_text:
                    softened["detected_intent"] = routing.intent_text
                return softened
            result = await orchestrator.patch(ui_id=resolved_ui_id, patch=patch, session_id=session_id)
            if resolved_ui_id != ui_id:
                result = dict(result)
                result["resolved_ui_id"] = resolved_ui_id
            return result

        if operation_key == "set_state":
            resolved_ui_id = await _resolve_target_ui_id(
                orchestrator,
                ui_id=ui_id,
                session_id=session_id,
            )
            if not resolved_ui_id:
                return {"success": False, "error": "`ui_id` is required for set_state (no active UI session found)."}
            if state is None:
                return {"success": False, "error": "`state` is required for set_state."}
            result = await orchestrator.set_state(ui_id=resolved_ui_id, state=state, session_id=session_id)
            softened = _soften_no_clients_result(result, operation="set_state")
            if desktop_pending_connection:
                softened.setdefault(
                    "warning",
                    "Desktop client is still connecting; state update queued and will apply when ready.",
                )
                softened["pending_client_connection"] = True
            if resolved_ui_id != ui_id:
                softened["resolved_ui_id"] = resolved_ui_id
            return softened

        if operation_key == "notify":
            if not message:
                return {"success": False, "error": "`message` is required for notify."}
            return await orchestrator.notify(
                ui_id=ui_id,
                message=message,
                level=level,
                session_id=session_id,
            )

        if operation_key == "close":
            resolved_ui_id = await _resolve_target_ui_id(
                orchestrator,
                ui_id=ui_id,
                session_id=session_id,
            )
            if not resolved_ui_id:
                return {"success": False, "error": "`ui_id` is required for close (no active UI session found)."}
            result = await orchestrator.close(ui_id=resolved_ui_id, session_id=session_id)
            if resolved_ui_id != ui_id:
                result = dict(result)
                result["resolved_ui_id"] = resolved_ui_id
            return result

        if operation_key == "list_sessions":
            return await orchestrator.list_sessions()

        if operation_key == "get_session":
            if not ui_id:
                return {"success": False, "error": "`ui_id` is required for get_session."}
            return await orchestrator.get_session(ui_id)

        if operation_key == "update_phase":
            resolved_ui_id = await _resolve_target_ui_id(
                orchestrator,
                ui_id=ui_id,
                session_id=session_id,
            )
            if not resolved_ui_id:
                return {"success": False, "error": "`ui_id` is required for update_phase (no active UI session found)."}
            target_phase = (phase or "").strip().lower()
            if not target_phase:
                return {"success": False, "error": "`phase` is required for update_phase."}
            allowed = {item.value for item in MetaUIPhase}
            if target_phase not in allowed:
                return {"success": False, "error": f"invalid phase: {phase}. allowed={sorted(allowed)}"}
            result = await orchestrator.update_phase(ui_id=resolved_ui_id, phase=target_phase, error=error)
            if resolved_ui_id != ui_id:
                result = dict(result)
                result["resolved_ui_id"] = resolved_ui_id
            return result

        if operation_key == "poll_events":
            return await orchestrator.get_events(
                ui_id=ui_id,
                session_id=session_id,
                event_types=event_types,
                since_ts=since_ts,
                limit=limit,
                consume=consume,
            )

        if operation_key == "wait_event":
            return await orchestrator.wait_event(
                ui_id=ui_id,
                session_id=session_id,
                event_types=event_types,
                timeout=_as_float(wait_timeout_seconds, 30.0),
                consume=consume,
            )

        return {"success": False, "error": f"Unhandled operation: {operation_key}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
