"""Scroll guard and recovery helpers for BrowserService."""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque, Dict, Optional

from .element_matching import (
    _find_editable_recovery_refs,
    _find_scroll_recovery_refs,
    _pick_confirm_recovery_ref,
    _pick_editable_recovery_ref,
)
from .service_constants import DEFAULT_SCROLL_RECOVERY_CLICK_TIMEOUT_MS
from .service_utils import _as_int, _as_str, _resolve_scroll_positions, _sign


class BrowserServiceScrollGuardMixin:
    def _record_scroll_event(
        self,
        *,
        profile: str,
        payload: Dict[str, Any],
        requested_delta_y: int,
    ) -> Optional[Dict[str, Any]]:
        target_id = _as_str(payload.get("target_id")) or "unknown"
        url = _as_str(payload.get("url")) or ""
        url_key = url.split("#", 1)[0][:160]
        before_y, after_y, position_source = _resolve_scroll_positions(payload)
        raw_container_meta = payload.get("active_container_scroll") or payload.get("container_scroll") or {}
        container_meta = raw_container_meta if isinstance(raw_container_meta, dict) else {}
        container_key = _as_str(container_meta.get("container_key")) or ""
        source_scope = f"{position_source}:{container_key[:96]}"
        key = f"{profile}:{target_id}:{url_key}:{source_scope}"

        history: Optional[Deque[Dict[str, Any]]] = self._scroll_history.get(key)
        if history is None:
            history = deque(maxlen=12)
            self._scroll_history[key] = history

        if before_y == after_y and position_source in {"container", "active_container"} and history:
            # Selector-based container scroll may only report current `top`.
            # Use previous sample as synthetic "before" to recover direction.
            prev_entry = history[-1]
            prev_after = _as_int(prev_entry.get("after_y"))
            prev_source = _as_str(prev_entry.get("source"))
            if prev_after is not None and prev_source == position_source:
                before_y = prev_after
        moved_delta = after_y - before_y
        direction = _sign(moved_delta if moved_delta != 0 else requested_delta_y)
        effective = bool(payload.get("scroll_effective"))
        requested_abs = max(1, abs(int(requested_delta_y)))
        progress_ratio = abs(int(moved_delta)) / float(requested_abs)
        no_progress = (not effective) or progress_ratio < 0.18
        if no_progress:
            self._scroll_no_progress_streak[profile] = int(self._scroll_no_progress_streak.get(profile, 0)) + 1
        else:
            self._scroll_no_progress_streak[profile] = 0
        history.append(
            {
                "before_y": before_y,
                "after_y": after_y,
                "direction": direction,
                "effective": effective,
                "progress_ratio": progress_ratio,
                "requested_delta_y": requested_delta_y,
                "source": position_source,
                "time": time.monotonic(),
            }
        )

        recent3 = list(history)[-3:]
        if len(recent3) == 3 and all(not e["effective"] for e in recent3):
            return {
                "code": "scroll_no_effect",
                "message": (
                    "Repeated scroll actions had no effect. Try a different strategy "
                    "(click target control, snapshot, or navigate) instead of looping scroll."
                ),
                "details": {
                    "category": "no_effect_repetition",
                    "profile": profile,
                    "target_id": target_id,
                    "url": url,
                    "source": position_source,
                },
            }

        if len(recent3) == 3:
            dirs3 = [int(e["direction"]) for e in recent3]
            ys3 = [int(e["after_y"]) for e in recent3]
            span3 = max(ys3) - min(ys3)
            net3 = abs(ys3[-1] - ys3[0])
            nonzero3 = [d for d in dirs3 if d != 0]
            direction_changes3 = 0
            for prev, cur in zip(nonzero3, nonzero3[1:]):
                if prev != cur:
                    direction_changes3 += 1
            early_alternating = (
                len(nonzero3) == 3
                and dirs3[0] == -dirs3[1]
                and dirs3[1] == -dirs3[2]
                and span3 <= 600
                and net3 <= 220
            )
            early_short_bounce = (
                direction_changes3 >= 2
                and span3 <= 400
                and net3 <= 180
            )
            if early_alternating or early_short_bounce:
                return {
                    "code": "scroll_oscillation",
                    "message": (
                        "Detected early scroll oscillation (short bounce loop). "
                        "Stop repeated scrolling and switch to a targeted action "
                        "(click/type/select/wait)."
                    ),
                    "details": {
                        "category": "oscillation",
                        "profile": profile,
                        "target_id": target_id,
                        "url": url,
                        "directions": dirs3,
                        "positions": ys3,
                        "source": position_source,
                        "early_detected": True,
                    },
                }

        recent4 = list(history)[-4:]
        if len(recent4) == 4:
            dirs = [int(e["direction"]) for e in recent4]
            ys = [int(e["after_y"]) for e in recent4]
            span = max(ys) - min(ys)
            net = abs(ys[-1] - ys[0])
            ineffective = sum(1 for e in recent4 if not e["effective"])
            direction_changes = 0
            nonzero_dirs = [d for d in dirs if d != 0]
            for prev, cur in zip(nonzero_dirs, nonzero_dirs[1:]):
                if prev != cur:
                    direction_changes += 1

            alternating = (
                all(d != 0 for d in dirs)
                and dirs[0] == -dirs[1]
                and dirs[1] == -dirs[2]
                and dirs[2] == -dirs[3]
            )
            oscillating_window = (
                direction_changes >= 2
                and span <= 2000
                and net <= max(400, span // 2)
            )
            stalled_bounce = ineffective >= 2 and span <= 1200

            if alternating or oscillating_window or stalled_bounce:
                return {
                    "code": "scroll_oscillation",
                    "message": (
                        "Detected scroll oscillation (up/down loop). Stop repeated scrolling "
                        "and switch to a targeted action (click/type/select/wait)."
                    ),
                    "details": {
                        "category": "oscillation",
                        "profile": profile,
                        "target_id": target_id,
                        "url": url,
                        "directions": dirs,
                        "positions": ys,
                        "ineffective_count": ineffective,
                        "source": position_source,
                    },
                }

        recent6 = list(history)[-6:]
        if len(recent6) == 6:
            ys6 = [int(e["after_y"]) for e in recent6]
            dirs6 = [int(e["direction"]) for e in recent6]
            unique_positions = len(set(ys6))
            direction_changes = 0
            nonzero = [d for d in dirs6 if d != 0]
            for prev, cur in zip(nonzero, nonzero[1:]):
                if prev != cur:
                    direction_changes += 1
            no_progress_count = sum(
                1
                for item in recent6
                if (not bool(item.get("effective")))
                or float(item.get("progress_ratio") or 0.0) < 0.18
            )
            if unique_positions <= 3 and direction_changes >= 3 and no_progress_count >= 3:
                return {
                    "code": "scroll_oscillation",
                    "message": (
                        "Detected repeated anchor oscillation while scrolling. "
                        "Switch to a targeted action (click/type/select/wait)."
                    ),
                    "details": {
                        "category": "oscillation",
                        "profile": profile,
                        "target_id": target_id,
                        "url": url,
                        "positions": ys6,
                        "unique_positions": unique_positions,
                        "direction_changes": direction_changes,
                        "no_progress_count": no_progress_count,
                        "source": position_source,
                    },
                }

        return None

    def _is_scroll_blocked(self, profile: str) -> bool:
        return profile in self._scroll_blocked_profiles

    def _block_scroll(self, profile: str) -> None:
        self._scroll_blocked_profiles.add(profile)

    def _clear_scroll_guard(self, profile: str) -> None:
        if profile in self._scroll_blocked_profiles:
            self._scroll_blocked_profiles.discard(profile)
        prefix = f"{profile}:"
        stale_keys = [key for key in self._scroll_history if key.startswith(prefix)]
        for key in stale_keys:
            self._scroll_history.pop(key, None)
        self._reset_scroll_request_state(profile)

    async def _build_scroll_recovery(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        target_id = _as_str(payload.get("target_id"))
        recovery: Dict[str, Any] = {
            "suggested_next_ops": ["snapshot", "click", "wait", "type", "select"],
        }
        if not target_id:
            return recovery
        nodes, resolved_target_id = await self._snapshot_nodes_for_resolution(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
        )
        if nodes is None:
            return recovery

        recovery["snapshot_target_id"] = resolved_target_id or target_id
        refs = _find_scroll_recovery_refs(nodes)
        if refs:
            recovery["suggested_refs"] = refs
        editable_refs = _find_editable_recovery_refs(nodes)
        if editable_refs:
            recovery["editable_refs"] = editable_refs
        return recovery

    async def _attempt_scroll_auto_recovery(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        payload: Dict[str, Any],
        recovery: Dict[str, Any],
        trigger_code: str,
    ) -> Optional[Dict[str, Any]]:
        refs = recovery.get("suggested_refs")
        editable_refs = recovery.get("editable_refs")
        selected_ref: Optional[str] = None
        # For oscillating form workflows, focusing an editable control first
        # is usually more stable than clicking a generic "Done/Search" action.
        if trigger_code == "scroll_oscillation" and isinstance(editable_refs, list):
            selected_ref = _pick_editable_recovery_ref(editable_refs)
        if not selected_ref and isinstance(refs, list):
            selected_ref = _pick_confirm_recovery_ref(refs)
        if not selected_ref and isinstance(editable_refs, list):
            selected_ref = _pick_editable_recovery_ref(editable_refs)
        if not selected_ref:
            return None
        target_id = _as_str(payload.get("target_id")) or _as_str(recovery.get("snapshot_target_id"))
        try:
            repaired = await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.click(
                    target_id=target_id,
                    timeout_ms=min(timeout_ms, DEFAULT_SCROLL_RECOVERY_CLICK_TIMEOUT_MS),
                    ref=selected_ref,
                ),
            )
        except Exception:
            return None
        repaired["auto_recovered"] = True
        repaired["recovery_action"] = "click"
        repaired["recovery_ref"] = selected_ref
        repaired["recovery_reason"] = trigger_code
        return repaired
