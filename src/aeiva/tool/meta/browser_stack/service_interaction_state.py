"""Interaction state helpers for browser service resilience."""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, Optional

from .service_constants import (
    DEFAULT_FIELD_TARGET_LOCK_USES,
    DEFAULT_SCROLL_NO_PROGRESS_TRIGGER,
    DEFAULT_SCROLL_REPEAT_LIMIT,
    DEFAULT_SCROLL_REQUEST_WINDOW_SECONDS,
)
from .service_utils import _as_int, _as_str


class BrowserServiceInteractionStateMixin:
    @staticmethod
    def _normalize_field_hint(value: Optional[str]) -> str:
        return str(value or "").strip().casefold()

    def _remember_field_target_lock(
        self,
        *,
        profile: str,
        target_id: Optional[str],
        operation: str,
        field_hint: Optional[str],
        ref: Optional[str],
    ) -> None:
        clean_ref = _as_str(ref)
        if not clean_ref:
            return
        clean_operation = _as_str(operation) or ""
        clean_hint = self._normalize_field_hint(field_hint)
        if not clean_hint:
            return
        uses = max(1, min(10, int(DEFAULT_FIELD_TARGET_LOCK_USES)))
        self._field_target_locks[profile] = {
            "target_id": _as_str(target_id) or "",
            "operation": clean_operation,
            "field_hint": clean_hint,
            "ref": clean_ref,
            "remaining_uses": uses,
        }

    def _consume_field_target_lock(
        self,
        *,
        profile: str,
        target_id: Optional[str],
        operation: str,
        field_hint: Optional[str],
    ) -> Optional[str]:
        state = self._field_target_locks.get(profile)
        if not isinstance(state, dict):
            return None
        lock_ref = _as_str(state.get("ref"))
        if not lock_ref:
            self._field_target_locks.pop(profile, None)
            return None
        lock_operation = _as_str(state.get("operation")) or ""
        if lock_operation and lock_operation != (_as_str(operation) or ""):
            return None
        lock_target = _as_str(state.get("target_id")) or ""
        active_target = _as_str(target_id) or ""
        if lock_target and active_target and lock_target != active_target:
            return None
        lock_hint = self._normalize_field_hint(_as_str(state.get("field_hint")))
        request_hint = self._normalize_field_hint(field_hint)
        if lock_hint and request_hint and lock_hint != request_hint:
            return None

        remaining = _as_int(state.get("remaining_uses")) or 0
        if remaining <= 1:
            self._field_target_locks.pop(profile, None)
        else:
            state["remaining_uses"] = remaining - 1
        return lock_ref

    def _clear_field_target_lock(self, profile: str) -> None:
        self._field_target_locks.pop(profile, None)

    def _check_scroll_request_budget(
        self,
        *,
        profile: str,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        delta_x: int,
        delta_y: int,
    ) -> Optional[Dict[str, Any]]:
        now = time.monotonic()
        history: Optional[Deque[Dict[str, Any]]] = self._scroll_request_history.get(profile)
        if history is None:
            history = deque(maxlen=24)
            self._scroll_request_history[profile] = history
        signature = "|".join(
            [
                _as_str(target_id) or "",
                _as_str(selector) or "",
                _as_str(ref) or "",
                str(int(delta_x)),
                str(int(delta_y)),
            ]
        )
        history.append({"signature": signature, "time": now})
        window = float(self._scroll_request_window_seconds or DEFAULT_SCROLL_REQUEST_WINDOW_SECONDS)
        cutoff = now - max(1.0, window)
        same_signature = [
            item
            for item in history
            if _as_str(item.get("signature")) == signature and float(item.get("time") or 0.0) >= cutoff
        ]
        if len(same_signature) < int(self._scroll_repeat_limit or DEFAULT_SCROLL_REPEAT_LIMIT):
            return None
        no_progress_streak = int(
            self._scroll_no_progress_streak.get(profile, 0)
            or 0
        )
        if no_progress_streak < int(self._scroll_no_progress_trigger or DEFAULT_SCROLL_NO_PROGRESS_TRIGGER):
            return None
        return {
            "code": "scroll_repetition_blocked",
            "message": (
                "Repeated identical scroll requests are not making progress. "
                "Switch strategy (click/type/select/wait) before more scrolling."
            ),
            "details": {
                "profile": profile,
                "repeat_count": len(same_signature),
                "window_seconds": window,
                "no_progress_streak": no_progress_streak,
            },
        }

    def _reset_scroll_request_state(self, profile: str) -> None:
        self._scroll_request_history.pop(profile, None)
        self._scroll_no_progress_streak.pop(profile, None)
