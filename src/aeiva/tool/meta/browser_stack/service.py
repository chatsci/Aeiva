"""
Browser V2 service facade.

This file keeps tool-level orchestration separate from the runtime implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import logging
import time
from typing import Any, Deque, Dict, Optional

from .element_matching import (
    _FILL_FIELDS_STEP_OPERATIONS,
    _find_click_target_from_nodes,
    _find_confirm_target_from_nodes,
    _find_select_target_from_nodes,
    _find_type_target_from_nodes,
)
from .fill_fields_engine import FillFieldsEngine, FillFieldsHelpers
from .search_engine import SearchEngine
from .security import BrowserSecurityPolicy
from .service_constants import (
    DEFAULT_FIELD_TARGET_LOCK_USES,
    DEFAULT_FILL_STEP_TIMEOUT_MS,
    DEFAULT_SCROLL_NO_PROGRESS_TRIGGER,
    DEFAULT_SCROLL_REPEAT_LIMIT,
    DEFAULT_SCROLL_REQUEST_WINDOW_SECONDS,
    DEFAULT_SNAPSHOT_RESOLVE_LIMIT,
)
from .service_actions import BrowserServiceActionsMixin
from .service_dispatch import BrowserServiceDispatchMixin
from .service_resolution import BrowserServiceResolutionMixin
from .service_utils import (
    _as_bool,
    _as_float,
    _as_int,
    _as_str,
    _build_fill_fields_field_key,
    _build_fill_fields_step_signature,
    _classify_launch_failure,
    _coalesce,
    _expand_fill_fields_shorthand,
    _extract_operation_name,
    _normalize_paths,
    _normalize_timeout,
    _normalize_values,
)
from .runtime import BrowserSessionManager, DEFAULT_TIMEOUT_MS

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class _ExecuteContext:
    operation: str
    op: str
    profile: str
    timeout_ms: int
    requested_headless: bool
    headless: bool
    target_id: Optional[str]
    url: Optional[str]
    selector: Optional[str]
    ref: Optional[str]
    text: Optional[str]
    method: str
    headers: Optional[Dict[str, str]]
    body: Optional[str]
    query: Optional[str]
    request: Dict[str, Any]
    full_page: bool
    image_type: str
    limit: int


class BrowserService(
    BrowserServiceDispatchMixin,
    BrowserServiceResolutionMixin,
    BrowserServiceActionsMixin,
):
    """Facade that maps browser tool operations onto runtime/session primitives."""

    SUPPORTED_OPERATIONS = {
        "status",
        "start",
        "stop",
        "profiles",
        "tabs",
        "open",
        "open_tab",
        "focus",
        "close",
        "close_tab",
        "navigate",
        "back",
        "forward",
        "reload",
        "click",
        "type",
        "set_number",
        "set_date",
        "fill_fields",
        "workflow",
        "submit",
        "press",
        "hover",
        "select",
        "choose_option",
        "drag",
        "scroll",
        "upload",
        "wait",
        "evaluate",
        "snapshot",
        "act",
        "screenshot",
        "pdf",
        "get_text",
        "get_html",
        "console",
        "errors",
        "network",
        "request",
        "search",
        "confirm",
    }

    def __init__(
        self,
        session_manager: Optional[BrowserSessionManager] = None,
        security_policy: Optional[BrowserSecurityPolicy] = None,
    ) -> None:
        self._sessions = session_manager or BrowserSessionManager()
        self._scroll_history: Dict[str, Deque[Dict[str, Any]]] = {}
        self._scroll_blocked_profiles: set[str] = set()
        self._field_target_locks: Dict[str, Dict[str, Any]] = {}
        self._scroll_request_history: Dict[str, Deque[Dict[str, Any]]] = {}
        self._scroll_no_progress_streak: Dict[str, int] = {}
        self._field_target_lock_uses = DEFAULT_FIELD_TARGET_LOCK_USES
        self._scroll_repeat_limit = DEFAULT_SCROLL_REPEAT_LIMIT
        self._scroll_request_window_seconds = DEFAULT_SCROLL_REQUEST_WINDOW_SECONDS
        self._scroll_no_progress_trigger = DEFAULT_SCROLL_NO_PROGRESS_TRIGGER
        self._security = security_policy or BrowserSecurityPolicy.from_env()
        self._search_engine = SearchEngine(service=self)
        self._fill_fields_engine = FillFieldsEngine(
            service=self,
            helpers=FillFieldsHelpers(
                as_str=_as_str,
                as_int=_as_int,
                as_bool=_as_bool,
                coalesce=_coalesce,
                normalize_timeout=_normalize_timeout,
                normalize_values=_normalize_values,
                normalize_paths=_normalize_paths,
                extract_operation_name=_extract_operation_name,
                expand_fill_fields_shorthand=_expand_fill_fields_shorthand,
                build_fill_fields_field_key=_build_fill_fields_field_key,
                build_fill_fields_step_signature=_build_fill_fields_step_signature,
            ),
            default_fill_step_timeout_ms=DEFAULT_FILL_STEP_TIMEOUT_MS,
            default_snapshot_resolve_limit=DEFAULT_SNAPSHOT_RESOLVE_LIMIT,
            supported_step_operations=_FILL_FIELDS_STEP_OPERATIONS,
        )

    async def execute(
        self,
        *,
        operation: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        query: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_MS,
        headless: bool = False,
        profile: str = "default",
        target_id: Optional[str] = None,
        ref: Optional[str] = None,
        request: Optional[Dict[str, Any]] = None,
        full_page: bool = False,
        image_type: str = "png",
        limit: int = 80,
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        op = (operation or "").strip().lower()
        profile_name = (profile or "default").strip() or "default"
        timeout_ms = _normalize_timeout(timeout)
        effective_headless = await self._effective_headless(profile_name, headless)
        request_payload = request or {}
        ctx = _ExecuteContext(
            operation=operation,
            op=op,
            profile=profile_name,
            timeout_ms=timeout_ms,
            requested_headless=headless,
            headless=effective_headless,
            target_id=target_id,
            url=url,
            selector=selector,
            ref=ref,
            text=text,
            method=method,
            headers=headers,
            body=body,
            query=query,
            request=request_payload,
            full_page=full_page,
            image_type=image_type,
            limit=limit,
        )
        act_kind = (_as_str(request_payload.get("kind")) or "").lower() if op == "act" else ""
        scroll_like = op == "scroll" or (op == "act" and act_kind == "scroll")
        should_clear_guard_after_success = not scroll_like
        if scroll_like and self._is_scroll_blocked(profile_name):
            return self._err(
                "Scroll is temporarily blocked after oscillation/no-effect detection. "
                "Run a targeted action (click/type/select/wait/navigate) before scrolling again.",
                code="scroll_blocked",
                details={
                    "profile": profile_name,
                    "suggested_next_ops": ["snapshot", "click", "type", "select", "wait", "navigate"],
                },
            )

        try:
            payload = await self._dispatch_execute(ctx)
            if payload is not None:
                if should_clear_guard_after_success and bool(payload.get("success")):
                    self._clear_scroll_guard(profile_name)
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.debug(
                    "browser.execute success op=%s profile=%s headless=%s duration_ms=%s",
                    op or operation,
                    profile_name,
                    effective_headless,
                    duration_ms,
                )
                return payload
            return self._err(
                f"Unknown operation: {operation}",
                code="unknown_operation",
                details={"supported_operations": sorted(self.SUPPORTED_OPERATIONS)},
            )
        except ValueError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.debug(
                "browser.execute invalid_request op=%s profile=%s duration_ms=%s error=%s",
                op or operation,
                profile_name,
                duration_ms,
                exc,
            )
            return self._err(str(exc), code="invalid_request")
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            message = str(exc)
            launch_details = _classify_launch_failure(message)
            if launch_details is not None:
                logger.warning(
                    "browser.execute launch_blocked op=%s profile=%s duration_ms=%s error=%s",
                    op or operation,
                    profile_name,
                    duration_ms,
                    message,
                )
                return self._err(message, code="launch_blocked", details=launch_details)
            logger.warning(
                "browser.execute runtime_error op=%s profile=%s duration_ms=%s error=%s",
                op or operation,
                profile_name,
                duration_ms,
                message,
            )
            return self._err(message, code="runtime_error")

    @staticmethod
    def _ok(**payload: Any) -> Dict[str, Any]:
        out = {"success": True, "error": None}
        out.update(payload)
        return out

    @staticmethod
    def _err(message: str, *, code: str = "browser_error", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": False,
            "error": message,
            "error_code": code,
        }
        if details:
            payload["error_details"] = details
        return payload

_BROWSER_SERVICE: Optional[BrowserService] = None


def get_browser_service() -> BrowserService:
    global _BROWSER_SERVICE
    if _BROWSER_SERVICE is None:
        _BROWSER_SERVICE = BrowserService()
    return _BROWSER_SERVICE


def set_browser_service(service: Optional[BrowserService]) -> None:
    global _BROWSER_SERVICE
    _BROWSER_SERVICE = service
