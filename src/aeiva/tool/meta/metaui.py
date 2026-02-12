"""
MetaUI Tool: channel-agnostic desktop UI orchestration.
"""

from __future__ import annotations

import atexit
import asyncio
from copy import deepcopy
from dataclasses import dataclass
import os
import subprocess
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional

from aeiva.metaui.desktop_runtime import resolve_desktop_python
from aeiva.metaui.spec_normalizer import (
    collect_interaction_contract_issues,
    normalize_metaui_spec,
)
from aeiva.metaui.component_catalog import get_component_catalog
from aeiva.metaui.a2ui_generation_contract import (
    get_available_presets,
    get_a2ui_generation_contract,
    get_interaction_fix_guide,
    resolve_preset_spec,
)
from aeiva.metaui.a2ui_protocol import get_protocol_schema_bundle
from aeiva.metaui.interaction_contract import get_interaction_contract_snapshot
from aeiva.metaui.message_evaluator import evaluate_server_messages
from aeiva.metaui.error_codes import ERROR_NO_CONNECTED_CLIENTS
from aeiva.metaui.orchestrator import (
    get_metaui_orchestrator,
    get_metaui_runtime_settings,
)
from aeiva.metaui.protocol import MetaUISpec
from aeiva.metaui.session import MetaUIPhase

from ..capability import Capability
from ..decorator import tool
from .metaui_state import (
    ActiveUIState as _ActiveUIState,
    DESKTOP_CONNECT_GRACE_SECONDS,
    DESKTOP_LAUNCH_COOLDOWN_SECONDS,
    DESKTOP_PENDING_ENV_VAR,
    DesktopLaunchState as _DesktopLaunchState,
)


_VALID_OPERATIONS = (
    "start",
    "status",
    "validate_spec",
    "catalog",
    "protocol_schema",
    "validate_messages",
    "launch_desktop",
    "render_full",
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
)
_VALID_OPERATION_KEYS = frozenset(_VALID_OPERATIONS)
_KNOWN_OPERATIONS = ", ".join(_VALID_OPERATIONS)


_DESKTOP_STATE = _DesktopLaunchState()
_ACTIVE_UI_STATE = _ActiveUIState()
_DESKTOP_CONNECT_GRACE_SECONDS = DESKTOP_CONNECT_GRACE_SECONDS
_DESKTOP_LAUNCH_COOLDOWN_SECONDS = DESKTOP_LAUNCH_COOLDOWN_SECONDS
_DESKTOP_PENDING_ENV_VAR = DESKTOP_PENDING_ENV_VAR


def _mark_desktop_connect_pending() -> None:
    _DESKTOP_STATE.mark_pending()


def _clear_desktop_connect_pending() -> None:
    _DESKTOP_STATE.clear_pending()


def _is_external_desktop_pending() -> bool:
    return _DESKTOP_STATE.is_external_pending()


def _try_claim_desktop_launch_slot() -> bool:
    return _DESKTOP_STATE.try_claim_slot()


def _register_launched_desktop_process(process: subprocess.Popen) -> None:
    _DESKTOP_STATE.register_process(process)


def _prune_dead_desktop_processes() -> None:
    _DESKTOP_STATE.prune_dead_processes()


def _get_live_desktop_process() -> Optional[subprocess.Popen]:
    return _DESKTOP_STATE.live_process()


def _cleanup_launched_desktops() -> None:
    _DESKTOP_STATE.cleanup_processes()


atexit.register(_cleanup_launched_desktops)


def _reset_desktop_launch_state_for_tests() -> None:
    _DESKTOP_STATE.reset()
    _ACTIVE_UI_STATE.reset()


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


def _remember_active_ui(*, ui_id: Optional[str], session_id: Optional[str]) -> None:
    _ACTIVE_UI_STATE.remember(ui_id=ui_id, session_id=session_id)


def _forget_active_ui(*, ui_id: Optional[str]) -> None:
    _ACTIVE_UI_STATE.forget(ui_id=ui_id)


def _preferred_active_ui(*, session_id: Optional[str]) -> Optional[str]:
    return _ACTIVE_UI_STATE.preferred(session_id=session_id)


def _soften_no_clients_result(
    result: Dict[str, Any],
    *,
    operation: str,
    allow_pending: bool,
) -> Dict[str, Any]:
    """Optionally convert no_connected_clients into a soft 'pending' success.

    Softening is intentionally opt-in. This prevents false-positive success
    responses unless the caller is explicitly in a desktop-connect grace window.
    """
    if result.get("success") is True:
        return result
    if str(result.get("error") or "") != ERROR_NO_CONNECTED_CLIENTS:
        return result
    if not allow_pending:
        return result
    softened = dict(result)
    softened["success"] = True
    softened["pending_client_connection"] = True
    softened.pop("ws_url", None)
    softened.setdefault(
        "warning",
        f"{operation} queued; UI will render when desktop client connects.",
    )
    return softened


def _has_pending_desktop_launch() -> bool:
    # Pending is only valid when we have a local live process or an external
    # launch marker still within grace window.
    if _get_live_desktop_process() is not None:
        return True
    return _is_external_desktop_pending()


def _allow_pending_client_soft_success(*, desktop_pending_connection: bool) -> bool:
    return bool(desktop_pending_connection or _has_pending_desktop_launch())


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

    available_ui_ids = {
        str(item.get("ui_id")).strip()
        for item in sessions
        if isinstance(item, dict) and str(item.get("ui_id") or "").strip()
    }
    preferred = _preferred_active_ui(session_id=session_id)
    if preferred and preferred in available_ui_ids:
        return preferred
    if preferred and preferred not in available_ui_ids:
        _forget_active_ui(ui_id=preferred)

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


@dataclass
class _RuntimeContext:
    settings: Any
    strict_component_types: bool
    orchestrator: Any
    endpoint: Any
    resolved_token: Optional[str]


@dataclass
class _OperationRequest:
    operation: str
    spec: Optional[Dict[str, Any]]
    patch: Optional[Dict[str, Any]]
    state: Optional[Dict[str, Any]]
    ui_id: Optional[str]
    session_id: Optional[str]
    message: Optional[str]
    level: str
    auto_ui: Optional[bool]
    phase: Optional[str]
    error: Optional[str]
    ensure_visible: bool
    wait_for_client_seconds: float
    wait_timeout_seconds: float
    limit: int
    consume: bool
    event_types: Optional[List[str]]
    since_ts: Optional[float]
    host: Optional[str]
    port: Optional[int]
    token: Optional[str]


OperationHandler = Callable[
    [_OperationRequest, _RuntimeContext, bool],
    Awaitable[Dict[str, Any]],
]


def _missing_operation_result() -> Dict[str, Any]:
    return {
        "success": False,
        "error_code": "operation_required",
        "error": "Missing required field: `operation`.",
        "hint": (
            "Call `metaui` with a valid operation string, for example: "
            "`status`, `catalog`, or `render_full`."
        ),
        "valid_operations": sorted(_VALID_OPERATION_KEYS),
    }


def _invalid_operation_result(operation: Optional[str]) -> Dict[str, Any]:
    shown = str(operation or "").strip() or "<empty>"
    return {
        "success": False,
        "error_code": "invalid_operation",
        "error": (
            f"Unknown operation: {shown}. "
            f"Valid operations: {_KNOWN_OPERATIONS}."
        ),
        "valid_operations": sorted(_VALID_OPERATION_KEYS),
    }


def _validate_spec_payload(
    spec: Dict[str, Any],
    *,
    strict_component_types: bool,
) -> Dict[str, Any]:
    normalized = normalize_metaui_spec(
        spec,
        strict_component_types=strict_component_types,
    )
    issues = collect_interaction_contract_issues(normalized)
    if issues:
        validation_errors = [
            _build_validation_error(
                issue,
                path_hint="/components",
            )
            for issue in issues
        ]
        return {
            "success": False,
            "error": "invalid interaction contract in spec",
            "error_code": "interaction_contract_invalid",
            "issues": issues,
            "validation_errors": validation_errors,
            "fix_guide": get_interaction_fix_guide(),
        }
    validated = MetaUISpec.model_validate(normalized).model_dump(mode="json")
    return {"success": True, "spec": validated}


def _infer_validation_path(message: str) -> str:
    text = str(message or "").strip()
    lowered = text.lower()
    if not text:
        return "/"
    if "root" in lowered:
        return "/root"
    if "component" in lowered or ".props" in lowered:
        return "/components"
    if "state" in lowered:
        return "/state"
    return "/"


def _build_validation_error(message: str, *, path_hint: Optional[str] = None) -> Dict[str, Any]:
    path = str(path_hint or "").strip() or _infer_validation_path(message)
    return {
        "code": "VALIDATION_FAILED",
        "path": path,
        "message": str(message),
    }


def _compact_protocol_schema_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    server_to_client = bundle.get("server_to_client")
    client_to_server = bundle.get("client_to_server")
    return {
        "version": bundle.get("version"),
        "sections": sorted(str(key) for key in bundle.keys()),
        "server_to_client_types": sorted(server_to_client.keys())
        if isinstance(server_to_client, dict)
        else [],
        "client_to_server_types": sorted(client_to_server.keys())
        if isinstance(client_to_server, dict)
        else [],
    }


def _compact_generation_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    compact = deepcopy(contract)
    examples = compact.pop("examples", [])
    compact["examples_summary"] = [
        {"name": str(item.get("name") or "")}
        for item in examples
        if isinstance(item, dict)
    ]

    loop = compact.get("loop")
    if isinstance(loop, list):
        compact["loop"] = [
            {"step": str(item.get("step") or "")}
            for item in loop
            if isinstance(item, dict) and str(item.get("step") or "").strip()
        ]

    rules = compact.get("rules")
    if isinstance(rules, list):
        compact["rules"] = [str(item) for item in rules[:4]]
    compact.pop("rules_text", None)

    function_catalog = compact.get("function_catalog")
    if isinstance(function_catalog, dict):
        return_types = function_catalog.get("return_types")
        compact["function_catalog"] = {
            "functions": sorted(return_types.keys())
            if isinstance(return_types, dict)
            else [],
            "standard": list(function_catalog.get("standard") or []),
            "extensions": list(function_catalog.get("extensions") or []),
        }

    compact["quick_start"] = {
        "preset_usage": "metaui(operation='render_full', spec={'preset':'chat_ui'})",
        "available_presets": get_available_presets(),
        "render_full_required_fields": [
            "title",
            "interaction_mode",
            "components",
            "root",
        ],
        "button_action_shape": get_interaction_fix_guide().get("button_action"),
        "value_binding_example": get_interaction_fix_guide().get("value_binding_example"),
        "interactive_contract": [
            "Button.props.action is required for every Button.",
            "TextField/CheckBox/ChoicePicker/Slider/DateTimeInput should bind props.value.path.",
            "Use functionCall for immediate local behavior; use event for server round-trip handling.",
        ],
        "component_tree_rules": [
            "Row/Column children must reference component ids.",
            "Card child must be a component id.",
            "List template: children={componentId:'...', path:'/state/list'}.",
        ],
        "minimal_render_full_spec": {
            "title": "Chat",
            "interaction_mode": "interactive",
            "components": [
                {"id": "title", "type": "Text", "props": {"text": "Chat"}},
                {
                    "id": "draft",
                    "type": "TextField",
                    "props": {"label": "Msg", "value": {"path": "/draft"}},
                },
                {"id": "send_label", "type": "Text", "props": {"text": "Send"}},
                {
                    "id": "send_btn",
                    "type": "Button",
                    "props": {
                        "child": "send_label",
                        "action": {
                            "event": {
                                "name": "chat_send",
                                "context": {"draft": {"path": "/draft"}},
                            }
                        },
                    },
                },
                {"id": "root", "type": "Column", "props": {"children": ["title", "draft", "send_btn"]}},
            ],
            "root": ["root"],
            "state": {"draft": ""},
        },
    }
    return compact


def _compact_interaction_contract_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    component_supported_events = snapshot.get("component_supported_events")
    function_catalog = snapshot.get("function_catalog")
    interactive_requirements = snapshot.get("interactive_requirements")

    summary: Dict[str, Any] = {
        "components_with_events": sorted(component_supported_events.keys())
        if isinstance(component_supported_events, dict)
        else [],
    }
    if isinstance(function_catalog, dict):
        summary["function_catalog"] = {
            "standard": list(function_catalog.get("standard") or []),
            "extensions": list(function_catalog.get("extensions") or []),
        }
    if isinstance(interactive_requirements, dict):
        summary["interactive_requirements"] = {
            "requires_actionable_component": bool(
                interactive_requirements.get("requires_actionable_component", True)
            ),
            "value_path_binding_components": list(
                interactive_requirements.get("value_path_binding_components") or []
            ),
        }
    return summary


def _static_operation_result(
    *,
    operation_key: str,
    spec: Optional[Dict[str, Any]],
    strict_component_types: bool,
) -> Optional[Dict[str, Any]]:
    if operation_key == "validate_spec":
        if spec is None:
            return {"success": False, "error": "`spec` is required for validate_spec."}
        try:
            return _validate_spec_payload(spec, strict_component_types=strict_component_types)
        except Exception as exc:
            message = str(exc)
            return {
                "success": False,
                "error": f"invalid spec: {message}",
                "error_code": "VALIDATION_FAILED",
                "validation_error": _build_validation_error(message),
            }

    if operation_key == "catalog":
        interaction_contract = get_interaction_contract_snapshot()
        return {
            "success": True,
            "catalog": get_component_catalog(),
            "generation_contract": get_a2ui_generation_contract(),
            "interaction_contract": interaction_contract,
            "recommended_flow": [
                "1) build explicit MetaUI spec in model output",
                "2) call metaui(operation='render_full', spec=...)",
                "3) call metaui(operation='set_state', ...) / metaui(operation='patch', ...) for updates",
                "4) call metaui(operation='catalog') only if component/function names are unknown",
            ],
        }

    if operation_key == "protocol_schema":
        include_full_schema = isinstance(spec, dict) and bool(
            spec.get("full_schema") or spec.get("include_full_schema")
        )
        schema_bundle = get_protocol_schema_bundle()
        generation_contract = get_a2ui_generation_contract()
        interaction_contract = get_interaction_contract_snapshot()
        compact_mode = not include_full_schema
        return {
            "success": True,
            "schema": (
                schema_bundle
                if include_full_schema
                else _compact_protocol_schema_bundle(schema_bundle)
            ),
            "generation_contract": generation_contract
            if include_full_schema
            else _compact_generation_contract(generation_contract),
            "schema_compact": compact_mode,
            "interaction_contract": {
                "policy": "strict",
                "requires_explicit_handlers": True,
                "snapshot": (
                    interaction_contract
                    if include_full_schema
                    else _compact_interaction_contract_snapshot(interaction_contract)
                ),
            },
            "hint": (
                "Default response is compact for latency. Pass spec={'full_schema': true} "
                "to fetch full schemas. Prefer metaui(operation='render_full', spec=...) for common UI requests."
            ),
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
        return {"success": True, "evaluation": evaluate_server_messages(messages)}
    return None


async def _resolve_runtime_context(
    *,
    settings: Any,
    host: Optional[str],
    port: Optional[int],
    token: Optional[str],
) -> _RuntimeContext:
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
    return _RuntimeContext(
        settings=settings,
        strict_component_types=bool(getattr(settings, "strict_component_types", True)),
        orchestrator=orchestrator,
        endpoint=endpoint,
        resolved_token=resolved_token,
    )


async def _wait_for_client_with_pending_tracking(
    orchestrator: Any,
    *,
    timeout: float,
) -> bool:
    connected = await orchestrator.wait_for_client(timeout=timeout)
    if connected:
        _clear_desktop_connect_pending()
    else:
        _mark_desktop_connect_pending()
    return connected


async def _wait_for_client_status(
    orchestrator: Any,
    *,
    timeout: float,
) -> Dict[str, bool]:
    connected = await _wait_for_client_with_pending_tracking(
        orchestrator,
        timeout=timeout,
    )
    return {
        "client_connected": connected,
        "desktop_pending_connection": not connected,
    }


async def _launch_or_reuse_desktop(
    *,
    context: _RuntimeContext,
    wait_for_client_seconds: float,
) -> Dict[str, Any]:
    existing = _get_live_desktop_process()
    if existing is not None:
        result = {"success": True, "pid": existing.pid, "reused_existing_window": True}
        client_status = await _wait_for_client_status(
            context.orchestrator,
            timeout=wait_for_client_seconds,
        )
        result.update(client_status)
    else:
        if not _try_claim_desktop_launch_slot():
            if not _has_pending_desktop_launch():
                _clear_desktop_connect_pending()
                return {
                    "success": False,
                    "error": ERROR_NO_CONNECTED_CLIENTS,
                    "error_code": "desktop_launch_unavailable",
                    "hint": (
                        "Desktop launch slot is unavailable and no pending desktop "
                        "window was detected. Retry `launch_desktop`."
                    ),
                    "ws_url": context.endpoint.ws_url,
                }
            return {
                "success": True,
                "pending_client_connection": True,
                "warning": "Desktop launch is in cooldown/grace period; reusing pending launch window.",
                "ws_url": context.endpoint.ws_url,
            }
        launch = await asyncio.to_thread(
            _try_launch_desktop,
            context.endpoint.ws_url,
            context.resolved_token,
        )
        result = dict(launch)
        if result.get("success"):
            client_status = await _wait_for_client_status(
                context.orchestrator,
                timeout=wait_for_client_seconds,
            )
            result.update(client_status)
        else:
            _clear_desktop_connect_pending()
    result["ws_url"] = context.endpoint.ws_url
    return result


async def _ensure_visible_desktop(
    *,
    context: _RuntimeContext,
    ensure_visible: bool,
    wait_for_client_seconds: float,
) -> Dict[str, Any]:
    if not ensure_visible:
        return {"success": True, "desktop_pending_connection": False}

    # Keep render-path latency bounded: verify connectivity quickly and then
    # rely on orchestrator replay if the desktop client finishes connecting later.
    connect_probe_timeout = max(0.25, min(wait_for_client_seconds, 1.5))

    status = await context.orchestrator.status()
    auto_enabled = bool(status.get("auto_ui", True))
    if not auto_enabled or int(status.get("connected_clients") or 0) > 0:
        return {"success": True, "desktop_pending_connection": False}

    existing = _get_live_desktop_process()
    if existing is not None:
        client_status = await _wait_for_client_status(
            context.orchestrator,
            timeout=connect_probe_timeout,
        )
        return {
            "success": True,
            "desktop_pending_connection": bool(client_status["desktop_pending_connection"]),
        }

    if not _try_claim_desktop_launch_slot():
        if _has_pending_desktop_launch():
            _mark_desktop_connect_pending()
            return {"success": True, "desktop_pending_connection": True}
        _clear_desktop_connect_pending()
        return {
            "success": False,
            "error": ERROR_NO_CONNECTED_CLIENTS,
            "error_code": "desktop_launch_unavailable",
            "hint": (
                "No desktop client is connected and no pending launch is in progress. "
                "Retry with `launch_desktop` or wait for desktop startup."
            ),
            "ws_url": context.endpoint.ws_url,
        }

    launch = await asyncio.to_thread(_try_launch_desktop, context.endpoint.ws_url, context.resolved_token)
    if not launch.get("success"):
        _clear_desktop_connect_pending()
        return {
            "success": False,
            "error": launch.get("error") or "failed to launch MetaUI desktop",
            "ws_url": context.endpoint.ws_url,
        }
    client_status = await _wait_for_client_status(
        context.orchestrator,
        timeout=connect_probe_timeout,
    )
    return {
        "success": True,
        "desktop_pending_connection": bool(client_status["desktop_pending_connection"]),
    }


def _softened_result(
    *,
    result: Dict[str, Any],
    operation: str,
    desktop_pending_connection: bool,
    pending_warning: Optional[str] = None,
) -> Dict[str, Any]:
    pending_allowed = _allow_pending_client_soft_success(
        desktop_pending_connection=desktop_pending_connection
    )
    if (
        str(result.get("error") or "") == ERROR_NO_CONNECTED_CLIENTS
        and pending_allowed
    ):
        pending_result = dict(result)
        pending_result["pending_client_connection"] = True
        if pending_warning:
            pending_result.setdefault("warning", pending_warning)
        softened = _soften_no_clients_result(
            pending_result,
            operation=operation,
            allow_pending=True,
        )
        softened["queued_for_replay"] = True
        return softened

    softened = _soften_no_clients_result(
        result,
        operation=operation,
        allow_pending=pending_allowed,
    )
    if pending_warning and desktop_pending_connection:
        softened.setdefault("warning", pending_warning)
        softened["pending_client_connection"] = True
    return softened


async def _resolve_ui_id_or_error(
    *,
    orchestrator: Any,
    ui_id: Optional[str],
    session_id: Optional[str],
    operation: str,
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    resolved_ui_id = await _resolve_target_ui_id(
        orchestrator,
        ui_id=ui_id,
        session_id=session_id,
    )
    if resolved_ui_id:
        return resolved_ui_id, None
    return None, {"success": False, "error": f"`ui_id` is required for {operation} (no active UI session found)."}


def _build_operation_request(
    *,
    operation: str,
    spec: Optional[Dict[str, Any]],
    patch: Optional[Dict[str, Any]],
    state: Optional[Dict[str, Any]],
    ui_id: Optional[str],
    session_id: Optional[str],
    message: Optional[str],
    level: str,
    auto_ui: Optional[bool],
    phase: Optional[str],
    error: Optional[str],
    ensure_visible: bool,
    wait_for_client_seconds: float,
    wait_timeout_seconds: float,
    limit: int,
    consume: bool,
    event_types: Optional[List[str]],
    since_ts: Optional[float],
    host: Optional[str],
    port: Optional[int],
    token: Optional[str],
) -> _OperationRequest:
    return _OperationRequest(
        operation=operation,
        spec=spec,
        patch=patch,
        state=state,
        ui_id=ui_id,
        session_id=session_id,
        message=message,
        level=level,
        auto_ui=auto_ui,
        phase=phase,
        error=error,
        ensure_visible=ensure_visible,
        wait_for_client_seconds=wait_for_client_seconds,
        wait_timeout_seconds=wait_timeout_seconds,
        limit=limit,
        consume=consume,
        event_types=event_types,
        since_ts=since_ts,
        host=host,
        port=port,
        token=token,
    )


async def _handle_start(
    _request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    return {
        "success": True,
        "running": True,
        "ws_url": context.endpoint.ws_url,
        "host": context.endpoint.host,
        "port": context.endpoint.port,
        "token_required": context.endpoint.token_required,
    }


async def _handle_status(
    _request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    return await context.orchestrator.status()


async def _handle_set_auto_ui(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    if request.auto_ui is None:
        return {"success": False, "error": "`auto_ui` is required for set_auto_ui."}
    return await context.orchestrator.set_auto_ui(request.auto_ui)


async def _handle_launch_desktop(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    return await _launch_or_reuse_desktop(
        context=context,
        wait_for_client_seconds=request.wait_for_client_seconds,
    )


async def _handle_render_full(
    request: _OperationRequest,
    context: _RuntimeContext,
    desktop_pending_connection: bool,
) -> Dict[str, Any]:
    if request.spec is None:
        return {"success": False, "error": "`spec` is required for render_full."}

    raw_spec = request.spec
    if isinstance(raw_spec, dict) and "preset" in raw_spec:
        preset_name = str(raw_spec.get("preset") or "").strip()
        preset_title = raw_spec.get("title")
        resolved_preset = resolve_preset_spec(preset_name, title=preset_title if isinstance(preset_title, str) else None)
        if resolved_preset is None:
            return {
                "success": False,
                "error": f"unknown preset: {preset_name!r}",
                "error_code": "unknown_preset",
                "available_presets": get_available_presets(),
            }
        raw_spec = resolved_preset

    try:
        render_spec = normalize_metaui_spec(
            raw_spec,
            strict_component_types=context.strict_component_types,
        )
    except Exception as exc:
        message = str(exc)
        return {
            "success": False,
            "error": f"invalid spec: {message}",
            "error_code": "invalid_spec",
            "validation_error": _build_validation_error(message),
            "hint": (
                "Use metaui(operation='catalog') and metaui(operation='protocol_schema') "
                "to construct canonical spec."
            ),
        }
    interaction_issues = collect_interaction_contract_issues(render_spec)
    if interaction_issues:
        return {
            "success": False,
            "error": "invalid interaction contract in spec",
            "error_code": "interaction_contract_invalid",
            "issues": interaction_issues,
            "validation_errors": [
                _build_validation_error(issue, path_hint="/components")
                for issue in interaction_issues
            ],
            "fix_guide": get_interaction_fix_guide(),
        }

    result = await context.orchestrator.render_full(
        spec=render_spec,
        session_id=request.session_id,
        ui_id=request.ui_id,
    )
    softened = _softened_result(
        result=result,
        operation="render_full",
        desktop_pending_connection=desktop_pending_connection,
        pending_warning="Desktop client is still connecting; command queued and will render when ready.",
    )
    if softened.get("success"):
        requested_ui_id = request.ui_id
        if requested_ui_id is None and isinstance(render_spec, dict):
            raw_ui = render_spec.get("ui_id")
            if isinstance(raw_ui, str) and raw_ui.strip():
                requested_ui_id = raw_ui.strip()
        _remember_active_ui(
            ui_id=(softened.get("ui_id") or requested_ui_id),
            session_id=(softened.get("session_id") or request.session_id),
        )
    return softened


async def _handle_patch(
    request: _OperationRequest,
    context: _RuntimeContext,
    desktop_pending_connection: bool,
) -> Dict[str, Any]:
    resolved_ui_id, resolve_error = await _resolve_ui_id_or_error(
        orchestrator=context.orchestrator,
        ui_id=request.ui_id,
        session_id=request.session_id,
        operation="patch",
    )
    if resolve_error is not None:
        return resolve_error
    if request.patch is None:
        return {"success": False, "error": "`patch` is required for patch."}
    patch_result = await context.orchestrator.patch(
        ui_id=resolved_ui_id,
        patch=request.patch,
        session_id=request.session_id,
    )
    softened = _softened_result(
        result=patch_result,
        operation="patch",
        desktop_pending_connection=desktop_pending_connection,
    )
    if resolved_ui_id != request.ui_id:
        softened["resolved_ui_id"] = resolved_ui_id
    if softened.get("success"):
        _remember_active_ui(ui_id=resolved_ui_id, session_id=request.session_id)
    return softened


async def _handle_set_state(
    request: _OperationRequest,
    context: _RuntimeContext,
    desktop_pending_connection: bool,
) -> Dict[str, Any]:
    resolved_ui_id, resolve_error = await _resolve_ui_id_or_error(
        orchestrator=context.orchestrator,
        ui_id=request.ui_id,
        session_id=request.session_id,
        operation="set_state",
    )
    if resolve_error is not None:
        return resolve_error
    if request.state is None:
        return {"success": False, "error": "`state` is required for set_state."}
    result = await context.orchestrator.set_state(
        ui_id=resolved_ui_id,
        state=request.state,
        session_id=request.session_id,
    )
    softened = _softened_result(
        result=result,
        operation="set_state",
        desktop_pending_connection=desktop_pending_connection,
        pending_warning="Desktop client is still connecting; state update queued and will apply when ready.",
    )
    if resolved_ui_id != request.ui_id:
        softened["resolved_ui_id"] = resolved_ui_id
    if softened.get("success"):
        _remember_active_ui(ui_id=resolved_ui_id, session_id=request.session_id)
    return softened


async def _handle_notify(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    if not request.message:
        return {"success": False, "error": "`message` is required for notify."}
    return await context.orchestrator.notify(
        ui_id=request.ui_id,
        message=request.message,
        level=request.level,
        session_id=request.session_id,
    )


async def _handle_close(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    resolved_ui_id, resolve_error = await _resolve_ui_id_or_error(
        orchestrator=context.orchestrator,
        ui_id=request.ui_id,
        session_id=request.session_id,
        operation="close",
    )
    if resolve_error is not None:
        return resolve_error
    result = await context.orchestrator.close(
        ui_id=resolved_ui_id,
        session_id=request.session_id,
    )
    if resolved_ui_id != request.ui_id:
        result = dict(result)
        result["resolved_ui_id"] = resolved_ui_id
    if result.get("success"):
        _forget_active_ui(ui_id=resolved_ui_id)
    return result


async def _handle_list_sessions(
    _request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    return await context.orchestrator.list_sessions()


async def _handle_get_session(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    if not request.ui_id:
        return {"success": False, "error": "`ui_id` is required for get_session."}
    result = await context.orchestrator.get_session(request.ui_id)
    if result.get("success"):
        session = result.get("session")
        resolved_session_id = session.get("session_id") if isinstance(session, dict) else None
        _remember_active_ui(ui_id=request.ui_id, session_id=resolved_session_id)
    return result


async def _handle_update_phase(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    resolved_ui_id, resolve_error = await _resolve_ui_id_or_error(
        orchestrator=context.orchestrator,
        ui_id=request.ui_id,
        session_id=request.session_id,
        operation="update_phase",
    )
    if resolve_error is not None:
        return resolve_error
    target_phase = (request.phase or "").strip().lower()
    if not target_phase:
        return {"success": False, "error": "`phase` is required for update_phase."}
    allowed = {item.value for item in MetaUIPhase}
    if target_phase not in allowed:
        return {"success": False, "error": f"invalid phase: {request.phase}. allowed={sorted(allowed)}"}
    result = await context.orchestrator.update_phase(
        ui_id=resolved_ui_id,
        phase=target_phase,
        error=request.error,
    )
    if resolved_ui_id != request.ui_id:
        result = dict(result)
        result["resolved_ui_id"] = resolved_ui_id
    if result.get("success"):
        _remember_active_ui(ui_id=resolved_ui_id, session_id=request.session_id)
    return result


async def _handle_poll_events(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    return await context.orchestrator.get_events(
        ui_id=request.ui_id,
        session_id=request.session_id,
        event_types=request.event_types,
        since_ts=request.since_ts,
        limit=request.limit,
        consume=request.consume,
    )


async def _handle_wait_event(
    request: _OperationRequest,
    context: _RuntimeContext,
    _desktop_pending_connection: bool,
) -> Dict[str, Any]:
    return await context.orchestrator.wait_event(
        ui_id=request.ui_id,
        session_id=request.session_id,
        event_types=request.event_types,
        timeout=_as_float(request.wait_timeout_seconds, 5.0),
        consume=request.consume,
    )


_PRE_VISIBILITY_OPERATION_HANDLERS: Dict[str, OperationHandler] = {
    "start": _handle_start,
    "status": _handle_status,
    "set_auto_ui": _handle_set_auto_ui,
    "launch_desktop": _handle_launch_desktop,
}

_POST_VISIBILITY_OPERATION_HANDLERS: Dict[str, OperationHandler] = {
    "render_full": _handle_render_full,
    "patch": _handle_patch,
    "set_state": _handle_set_state,
    "notify": _handle_notify,
    "close": _handle_close,
    "list_sessions": _handle_list_sessions,
    "get_session": _handle_get_session,
    "update_phase": _handle_update_phase,
    "poll_events": _handle_poll_events,
    "wait_event": _handle_wait_event,
}


async def _dispatch_operation(
    *,
    handlers: Dict[str, OperationHandler],
    request: _OperationRequest,
    context: _RuntimeContext,
    desktop_pending_connection: bool,
) -> Optional[Dict[str, Any]]:
    handler = handlers.get(request.operation)
    if handler is None:
        return None
    return await handler(request, context, desktop_pending_connection)


@tool(
    description=(
        "Render desktop UI windows. "
        f"Operations: {_KNOWN_OPERATIONS}. "
        "Fast path for common UIs: metaui(operation='render_full', spec={'preset':'chat_ui'}) or "
        "metaui(operation='render_full', spec={'preset':'form_ui'}). "
        "Pass explicit A2UI spec with components/root/state for render_full. "
        "Use catalog/protocol_schema when you need schema and component contracts."
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
    ensure_visible: bool = True,
    wait_for_client_seconds: float = 8.0,
    wait_timeout_seconds: float = 5.0,
    limit: int = 50,
    consume: bool = False,
    event_types: Optional[List[str]] = None,
    since_ts: Optional[float] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    MetaUI desktop operations.

    Args:
        operation: The operation to perform (e.g. render_full, patch, set_state, status).
        spec: Full MetaUI spec dict for render_full.
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
        raw_operation = str(operation or "").strip()
        if not raw_operation:
            return _missing_operation_result()
        operation_key = raw_operation.lower()
        if operation_key not in _VALID_OPERATION_KEYS:
            return _invalid_operation_result(raw_operation)
        request = _build_operation_request(
            operation=operation_key,
            spec=spec,
            patch=patch,
            state=state,
            ui_id=ui_id,
            session_id=session_id,
            message=message,
            level=level,
            auto_ui=auto_ui,
            phase=phase,
            error=error,
            ensure_visible=ensure_visible,
            wait_for_client_seconds=wait_for_client_seconds,
            wait_timeout_seconds=wait_timeout_seconds,
            limit=limit,
            consume=consume,
            event_types=event_types,
            since_ts=since_ts,
            host=host,
            port=port,
            token=token,
        )

        settings = get_metaui_runtime_settings()
        static_result = _static_operation_result(
            operation_key=operation_key,
            spec=spec,
            strict_component_types=bool(getattr(settings, "strict_component_types", True)),
        )
        if static_result is not None:
            return static_result

        if not settings.enabled:
            return {"success": False, "error": "metaui is disabled by configuration"}

        context = await _resolve_runtime_context(
            settings=settings,
            host=request.host,
            port=request.port,
            token=request.token,
        )
        pre_result = await _dispatch_operation(
            handlers=_PRE_VISIBILITY_OPERATION_HANDLERS,
            request=request,
            context=context,
            desktop_pending_connection=False,
        )
        if pre_result is not None:
            return pre_result

        visibility_result = await _ensure_visible_desktop(
            context=context,
            ensure_visible=request.ensure_visible,
            wait_for_client_seconds=request.wait_for_client_seconds,
        )
        if not visibility_result.get("success"):
            return visibility_result
        desktop_pending_connection = bool(visibility_result.get("desktop_pending_connection"))
        post_result = await _dispatch_operation(
            handlers=_POST_VISIBILITY_OPERATION_HANDLERS,
            request=request,
            context=context,
            desktop_pending_connection=desktop_pending_connection,
        )
        if post_result is not None:
            return post_result

        return {"success": False, "error": f"Unhandled operation: {operation_key}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
