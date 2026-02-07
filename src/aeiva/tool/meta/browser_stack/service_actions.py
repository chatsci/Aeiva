"""Action execution mixin for BrowserService."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, Dict, Optional

from .element_matching import _is_stale_target_error
from .service_constants import DEFAULT_SCROLL_RECOVERY_CLICK_TIMEOUT_MS
from .service_runtime_ops import BrowserServiceRuntimeOpsMixin
from .service_utils import (
    _as_bool,
    _as_int,
    _as_str,
    _coalesce,
    _normalize_values,
)

if TYPE_CHECKING:
    from .service import _ExecuteContext

logger = logging.getLogger(__name__)


class BrowserServiceActionsMixin(BrowserServiceRuntimeOpsMixin):
    @staticmethod
    def _compute_attempt_timeout(
        *,
        timeout_ms: int,
        attempts: int,
        minimum: int = 350,
        maximum: int = 6000,
    ) -> int:
        clean_attempts = max(1, int(attempts))
        per_attempt = max(1, int(timeout_ms)) // clean_attempts
        return max(minimum, min(maximum, per_attempt))

    @staticmethod
    def _extract_numeric_token(text: str) -> Optional[float]:
        match = re.search(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", "."))
        if not match:
            return None
        try:
            return float(match.group(0))
        except Exception:
            return None

    @classmethod
    def _field_value_matches_expected(cls, field_value: Optional[str], expected: str) -> bool:
        if field_value is None:
            # When runtime doesn't expose a post-state value, keep legacy behavior.
            return True
        got = str(field_value).strip().casefold()
        exp = str(expected).strip().casefold()
        if not got:
            return not exp
        if got == exp or exp in got or got in exp:
            return True
        got_num = cls._extract_numeric_token(got)
        exp_num = cls._extract_numeric_token(exp)
        if got_num is not None and exp_num is not None:
            return abs(got_num - exp_num) < 1e-4
        return False

    @classmethod
    def _selected_values_match_expected(
        cls,
        selected_values: Any,
        expected_values: list[str],
    ) -> bool:
        if not isinstance(selected_values, list):
            # When runtime can't read selected values, keep legacy behavior.
            return True
        normalized_selected = [str(item).strip().casefold() for item in selected_values if str(item).strip()]
        if not normalized_selected:
            return False
        expected = [str(item).strip().casefold() for item in expected_values if str(item).strip()]
        if not expected:
            return True
        for item in expected:
            if item in normalized_selected:
                continue
            item_num = cls._extract_numeric_token(item)
            matched_numeric = False
            if item_num is not None:
                for selected in normalized_selected:
                    selected_num = cls._extract_numeric_token(selected)
                    if selected_num is not None and abs(selected_num - item_num) < 1e-4:
                        matched_numeric = True
                        break
            if not matched_numeric:
                return False
        return True

    async def _run_set_operation(
        self,
        *,
        ctx: _ExecuteContext,
        operation: str,
    ) -> Dict[str, Any]:
        set_req = dict(ctx.request)
        value = _as_str(set_req.get("value")) or _as_str(set_req.get("text")) or _as_str(ctx.text)
        if value is None:
            return self._err(f"value required for {operation} operation")
        set_req["text"] = value
        if operation == "set_number" and not (
            _as_str(set_req.get("field"))
            or _as_str(set_req.get("label"))
            or _as_str(set_req.get("name"))
        ):
            set_req["field"] = "number"
        if operation == "set_date" and not (
            _as_str(set_req.get("field"))
            or _as_str(set_req.get("label"))
            or _as_str(set_req.get("name"))
        ):
            set_req["field"] = "date"
        payload = await self._run_type(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            text=value,
            url=ctx.url,
            request=set_req,
        )
        payload[operation] = True
        if operation == "set_date" and _as_bool(set_req.get("confirm"), default=False):
            confirm_request = dict(set_req)
            confirm_request.setdefault("confirm_context", "date_picker")
            confirm_text = _as_str(confirm_request.get("confirm_text"))
            confirm_payload = await self._run_confirm(
                profile=ctx.profile,
                headless=ctx.headless,
                timeout_ms=ctx.timeout_ms,
                target_id=_as_str(payload.get("target_id")) or ctx.target_id,
                selector=_as_str(confirm_request.get("confirm_selector")),
                ref=_as_str(confirm_request.get("confirm_ref")),
                text=confirm_text,
                request=confirm_request,
            )
            payload.update(confirm_payload)
        return self._ok(**payload)

    async def _finalize_scroll_payload(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        payload: Dict[str, Any],
        requested_delta_y: int,
        auto_recover: bool,
    ) -> Dict[str, Any]:
        guard = self._record_scroll_event(
            profile=profile,
            payload=payload,
            requested_delta_y=requested_delta_y,
        )
        if guard is None:
            return self._ok(**payload)
        self._block_scroll(profile)
        details = dict(guard.get("details") or {})
        recovery = await self._build_scroll_recovery(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            payload=payload,
        )
        if recovery:
            details.update(recovery)
            details["recovery"] = recovery
        if auto_recover:
            repaired = await self._attempt_scroll_auto_recovery(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                payload=payload,
                recovery=recovery,
                trigger_code=str(guard.get("code") or ""),
            )
            if repaired is not None:
                self._clear_scroll_guard(profile)
                return self._ok(**repaired)
            details.setdefault("auto_recover_failed", True)
        return self._err(
            str(guard.get("message") or "Scroll guard triggered."),
            code=str(guard.get("code") or "scroll_guard"),
            details=details or None,
        )

    async def _run_scroll_action(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        delta_x = _coalesce(
            _as_int(request.get("delta_x")),
            _as_int(request.get("deltaX")),
            0,
        )
        delta_y = _coalesce(
            _as_int(request.get("delta_y")),
            _as_int(request.get("deltaY")),
            800,
        )
        auto_recover = _as_bool(request.get("auto_recover"), default=True)
        budget_guard = self._check_scroll_request_budget(
            profile=profile,
            target_id=target_id,
            selector=selector,
            ref=ref,
            delta_x=int(delta_x),
            delta_y=int(delta_y),
        )
        if budget_guard is not None:
            self._block_scroll(profile)
            return self._err(
                str(budget_guard.get("message") or "scroll guard triggered"),
                code=str(budget_guard.get("code") or "scroll_guard"),
                details=dict(budget_guard.get("details") or {}),
            )
        payload = await self._runtime_scroll(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=selector,
            ref=ref,
            delta_x=int(delta_x),
            delta_y=int(delta_y),
        )
        return await self._finalize_scroll_payload(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            payload=payload,
            requested_delta_y=int(delta_y),
            auto_recover=auto_recover,
        )

    async def _run_click(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        text: Optional[str],
        url: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        click_req = request or {}
        active_target = target_id
        navigate_url = _as_str(click_req.get("url")) or _as_str(url)
        if navigate_url:
            nav_payload = await self._runtime_navigate(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=active_target,
                url=navigate_url,
            )
            active_target = _as_str(nav_payload.get("target_id")) or active_target

        resolved_selector = selector or _as_str(click_req.get("selector"))
        resolved_ref = ref or _as_str(click_req.get("ref"))
        fallback_targets: list[Dict[str, Any]] = []
        if not resolved_selector and not resolved_ref:
            query = _as_str(click_req.get("text")) or _as_str(text)
            if query:
                targets = await self._resolve_click_targets_from_snapshot(
                    profile=profile,
                    headless=headless,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                    query_text=query,
                    max_results=3,
                )
                if targets:
                    target = targets[0]
                    resolved_ref = target.get("ref")
                    active_target = target.get("target_id") or active_target
                    fallback_targets = targets[1:]
        if not resolved_selector and not resolved_ref:
            raise ValueError("click operation requires selector/ref/text target")

        click_timeout = self._compute_attempt_timeout(
            timeout_ms=timeout_ms,
            attempts=1 + len(fallback_targets),
        )

        async def _invoke_click(
            *,
            invoke_target: Optional[str],
            invoke_ref: Optional[str],
        ) -> Dict[str, Any]:
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.click(
                    target_id=invoke_target,
                    timeout_ms=click_timeout,
                    selector=resolved_selector,
                    ref=invoke_ref,
                    double_click=_as_bool(click_req.get("double_click"), default=False),
                    button=_as_str(click_req.get("button")) or "left",
                ),
            )

        try:
            payload = await _invoke_click(
                invoke_target=active_target,
                invoke_ref=resolved_ref,
            )
        except Exception as primary_exc:
            if resolved_selector or not fallback_targets:
                raise
            recovered = False
            last_exc: Exception = primary_exc
            for candidate in fallback_targets:
                candidate_ref = _as_str(candidate.get("ref"))
                if not candidate_ref or candidate_ref == resolved_ref:
                    continue
                candidate_target = _as_str(candidate.get("target_id")) or active_target
                try:
                    payload = await _invoke_click(
                        invoke_target=candidate_target,
                        invoke_ref=candidate_ref,
                    )
                    resolved_ref = candidate_ref
                    active_target = candidate_target
                    logger.debug(
                        "Recovered click by switching candidate profile=%s ref=%s",
                        profile,
                        candidate_ref,
                    )
                    recovered = True
                    break
                except Exception as candidate_exc:
                    last_exc = candidate_exc
            if not recovered:
                raise last_exc
        if resolved_ref:
            payload["resolved_ref"] = resolved_ref
        return payload

    async def _run_confirm(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        text: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        confirm_req = request or {}
        resolved_ref = ref or _as_str(confirm_req.get("ref"))
        resolved_selector = selector or _as_str(confirm_req.get("selector"))
        resolved_text = _as_str(confirm_req.get("text")) or _as_str(text)
        active_target = target_id or _as_str(confirm_req.get("target_id")) or _as_str(confirm_req.get("targetId"))
        confirm_context = (
            _as_str(confirm_req.get("confirm_context"))
            or _as_str(confirm_req.get("confirmContext"))
            or _as_str(confirm_req.get("context"))
        )
        resolved_node: Optional[Dict[str, Any]] = None

        if not resolved_ref and not resolved_selector:
            target = await self._resolve_confirm_target_from_snapshot(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=active_target,
                query_text=resolved_text,
                context=confirm_context,
            )
            if target is None:
                fallback = await self._attempt_confirm_enter_fallback(
                    profile=profile,
                    headless=headless,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                    reason="confirm_control_not_found",
                )
                if fallback is not None:
                    return fallback
                raise ValueError(
                    "confirm could not find an actionable confirmation control. "
                    "Call snapshot and pass the confirmation ref explicitly."
                )
            resolved_ref = target.get("ref")
            active_target = target.get("target_id") or active_target
            maybe_node = target.get("node")
            if isinstance(maybe_node, dict):
                resolved_node = maybe_node

        payload = await self._run_click(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=active_target,
            selector=resolved_selector,
            ref=resolved_ref,
            text=resolved_text,
            url=None,
            request=confirm_req,
        )
        payload["confirmed"] = True
        payload["confirm_action"] = True
        if resolved_node:
            payload["resolved_node"] = resolved_node
        return payload

    async def _attempt_confirm_enter_fallback(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        reason: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            pressed = await self._runtime_press(
                profile=profile,
                headless=headless,
                timeout_ms=min(timeout_ms, DEFAULT_SCROLL_RECOVERY_CLICK_TIMEOUT_MS),
                target_id=target_id,
                key="Enter",
            )
        except Exception:
            return None
        payload = dict(pressed)
        payload["confirmed"] = True
        payload["confirm_action"] = True
        payload["confirm_fallback"] = "press_enter"
        payload["fallback"] = "enter_key"
        payload["fallback_reason"] = reason
        return payload

    async def _run_type(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        text: Optional[str],
        url: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        type_req = request or {}
        value = _as_str(type_req.get("text")) or _as_str(text) or _as_str(url)
        if value is None:
            raise ValueError("text required for type operation")
        default_slow = _as_bool(type_req.get("slowly"), default=False)
        active_target = target_id
        resolved_selector = selector or _as_str(type_req.get("selector"))
        resolved_ref = ref or _as_str(type_req.get("ref"))
        resolved_node: Optional[Dict[str, Any]] = None
        fallback_targets: list[Dict[str, Any]] = []
        field_hint = _coalesce(
            _as_str(type_req.get("field")),
            _as_str(type_req.get("label")),
            _as_str(type_req.get("name")),
        )
        used_target_lock = False

        if not resolved_selector and not resolved_ref:
            locked_ref = self._consume_field_target_lock(
                profile=profile,
                target_id=active_target,
                operation="type",
                field_hint=field_hint,
            )
            if locked_ref:
                resolved_ref = locked_ref
                used_target_lock = True
            else:
                targets = await self._resolve_type_targets_from_snapshot(
                    profile=profile,
                    headless=headless,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                    value_text=value,
                    field_hint=field_hint,
                    max_results=3,
                )
                if targets:
                    target = targets[0]
                    resolved_ref = target.get("ref")
                    active_target = target.get("target_id") or active_target
                    maybe_node = target.get("node")
                    if isinstance(maybe_node, dict):
                        resolved_node = maybe_node
                    fallback_targets = targets[1:]

        attempt_timeout = self._compute_attempt_timeout(
            timeout_ms=timeout_ms,
            attempts=1 + len(fallback_targets),
        )

        async def _invoke_type(
            *,
            invoke_target: Optional[str],
            invoke_ref: Optional[str],
            slowly_override: bool,
        ) -> Dict[str, Any]:
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.type_text(
                    text=value,
                    target_id=invoke_target,
                    timeout_ms=attempt_timeout,
                    selector=resolved_selector,
                    ref=invoke_ref,
                    submit=_as_bool(type_req.get("submit"), default=False),
                    slowly=slowly_override,
                ),
            )

        def _postcondition_ok(payload: Dict[str, Any]) -> bool:
            return self._field_value_matches_expected(
                _as_str(payload.get("field_value")),
                value,
            )

        try:
            payload = await _invoke_type(
                invoke_target=active_target,
                invoke_ref=resolved_ref,
                slowly_override=default_slow,
            )
        except Exception as primary_exc:
            if used_target_lock and not resolved_selector:
                self._clear_field_target_lock(profile)
                used_target_lock = False
                targets = await self._resolve_type_targets_from_snapshot(
                    profile=profile,
                    headless=headless,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                    value_text=value,
                    field_hint=field_hint,
                    max_results=3,
                )
                if targets:
                    target = targets[0]
                    resolved_ref = target.get("ref")
                    active_target = target.get("target_id") or active_target
                    maybe_node = target.get("node")
                    if isinstance(maybe_node, dict):
                        resolved_node = maybe_node
                    fallback_targets = targets[1:]
                payload = await _invoke_type(
                    invoke_target=active_target,
                    invoke_ref=resolved_ref,
                    slowly_override=default_slow,
                )
                primary_exc = None  # no longer relevant after successful lock fallback
            if primary_exc is None:
                pass
            elif resolved_selector or not fallback_targets or not _is_stale_target_error(str(primary_exc)):
                raise
            else:
                recovered = False
                last_exc: Exception = primary_exc
                for candidate in fallback_targets:
                    candidate_ref = _as_str(candidate.get("ref"))
                    if not candidate_ref or candidate_ref == resolved_ref:
                        continue
                    candidate_target = _as_str(candidate.get("target_id")) or active_target
                    try:
                        payload = await _invoke_type(
                            invoke_target=candidate_target,
                            invoke_ref=candidate_ref,
                            slowly_override=default_slow,
                        )
                        resolved_ref = candidate_ref
                        active_target = candidate_target
                        maybe_node = candidate.get("node")
                        resolved_node = maybe_node if isinstance(maybe_node, dict) else None
                        recovered = True
                        break
                    except Exception as candidate_exc:
                        last_exc = candidate_exc
                if not recovered:
                    raise last_exc

        if not _postcondition_ok(payload):
            recovered = False
            last_post_exc: Optional[Exception] = None
            for candidate in fallback_targets:
                candidate_ref = _as_str(candidate.get("ref"))
                if not candidate_ref or candidate_ref == resolved_ref:
                    continue
                candidate_target = _as_str(candidate.get("target_id")) or active_target
                try:
                    payload_candidate = await _invoke_type(
                        invoke_target=candidate_target,
                        invoke_ref=candidate_ref,
                        slowly_override=default_slow,
                    )
                except Exception as candidate_exc:
                    last_post_exc = candidate_exc
                    continue
                if not _postcondition_ok(payload_candidate):
                    continue
                payload = payload_candidate
                resolved_ref = candidate_ref
                active_target = candidate_target
                maybe_node = candidate.get("node")
                resolved_node = maybe_node if isinstance(maybe_node, dict) else None
                recovered = True
                logger.debug(
                    "Recovered type by switching candidate profile=%s ref=%s",
                    profile,
                    candidate_ref,
                )
                break

            if not recovered and not default_slow:
                slow_retry = await _invoke_type(
                    invoke_target=active_target,
                    invoke_ref=resolved_ref,
                    slowly_override=True,
                )
                if _postcondition_ok(slow_retry):
                    payload = slow_retry
                    recovered = True
                    logger.debug(
                        "Recovered type via slow typing retry profile=%s ref=%s",
                        profile,
                        resolved_ref,
                    )

            if not recovered and not _postcondition_ok(payload):
                if last_post_exc is not None:
                    raise last_post_exc
                raise ValueError(
                    "type operation completed but field value did not reflect requested text"
                )
        if resolved_ref:
            payload["resolved_ref"] = resolved_ref
            self._remember_field_target_lock(
                profile=profile,
                target_id=active_target,
                operation="type",
                field_hint=field_hint,
                ref=resolved_ref,
            )
        if resolved_node:
            payload["resolved_node"] = resolved_node
        return payload

    async def _run_select(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        select_req = request or {}
        raw_values = select_req.get("values")
        if raw_values is None and select_req.get("value") is not None:
            raw_values = select_req.get("value")
        values = _normalize_values(raw_values)
        active_target = target_id
        resolved_selector = selector or _as_str(select_req.get("selector"))
        resolved_ref = ref or _as_str(select_req.get("ref"))
        resolved_node: Optional[Dict[str, Any]] = None
        fallback_targets: list[Dict[str, Any]] = []
        field_hint = (
            _as_str(select_req.get("field"))
            or _as_str(select_req.get("label"))
            or _as_str(select_req.get("name"))
        )
        used_target_lock = False

        if not resolved_selector and not resolved_ref:
            locked_ref = self._consume_field_target_lock(
                profile=profile,
                target_id=active_target,
                operation="select",
                field_hint=field_hint,
            )
            if locked_ref:
                resolved_ref = locked_ref
                used_target_lock = True
            else:
                targets = await self._resolve_select_targets_from_snapshot(
                    profile=profile,
                    headless=headless,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                    values=values,
                    field_hint=field_hint,
                    max_results=3,
                )
                if targets:
                    target = targets[0]
                    resolved_ref = target.get("ref")
                    active_target = target.get("target_id") or active_target
                    maybe_node = target.get("node")
                    if isinstance(maybe_node, dict):
                        resolved_node = maybe_node
                    fallback_targets = targets[1:]

        attempt_timeout = self._compute_attempt_timeout(
            timeout_ms=timeout_ms,
            attempts=1 + len(fallback_targets),
        )

        async def _invoke_select(
            *,
            invoke_target: Optional[str],
            invoke_ref: Optional[str],
        ) -> Dict[str, Any]:
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.select(
                    values=values,
                    target_id=invoke_target,
                    timeout_ms=attempt_timeout,
                    selector=resolved_selector,
                    ref=invoke_ref,
                ),
            )

        def _postcondition_ok(payload: Dict[str, Any]) -> bool:
            return self._selected_values_match_expected(
                payload.get("selected_values"),
                values,
            )

        try:
            payload = await _invoke_select(
                invoke_target=active_target,
                invoke_ref=resolved_ref,
            )
        except Exception as primary_exc:
            if used_target_lock and not resolved_selector:
                self._clear_field_target_lock(profile)
                used_target_lock = False
                targets = await self._resolve_select_targets_from_snapshot(
                    profile=profile,
                    headless=headless,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                    values=values,
                    field_hint=field_hint,
                    max_results=3,
                )
                if targets:
                    target = targets[0]
                    resolved_ref = target.get("ref")
                    active_target = target.get("target_id") or active_target
                    maybe_node = target.get("node")
                    if isinstance(maybe_node, dict):
                        resolved_node = maybe_node
                    fallback_targets = targets[1:]
                payload = await _invoke_select(
                    invoke_target=active_target,
                    invoke_ref=resolved_ref,
                )
                primary_exc = None
            if primary_exc is None:
                pass
            elif resolved_selector or not fallback_targets:
                raise
            else:
                recovered = False
                last_exc: Exception = primary_exc
                for candidate in fallback_targets:
                    candidate_ref = _as_str(candidate.get("ref"))
                    if not candidate_ref or candidate_ref == resolved_ref:
                        continue
                    candidate_target = _as_str(candidate.get("target_id")) or active_target
                    try:
                        payload = await _invoke_select(
                            invoke_target=candidate_target,
                            invoke_ref=candidate_ref,
                        )
                        resolved_ref = candidate_ref
                        active_target = candidate_target
                        maybe_node = candidate.get("node")
                        resolved_node = maybe_node if isinstance(maybe_node, dict) else None
                        recovered = True
                        break
                    except Exception as candidate_exc:
                        last_exc = candidate_exc
                if not recovered:
                    raise last_exc

        if not _postcondition_ok(payload):
            recovered = False
            last_post_exc: Optional[Exception] = None
            for candidate in fallback_targets:
                candidate_ref = _as_str(candidate.get("ref"))
                if not candidate_ref or candidate_ref == resolved_ref:
                    continue
                candidate_target = _as_str(candidate.get("target_id")) or active_target
                try:
                    payload_candidate = await _invoke_select(
                        invoke_target=candidate_target,
                        invoke_ref=candidate_ref,
                    )
                except Exception as candidate_exc:
                    last_post_exc = candidate_exc
                    continue
                if not _postcondition_ok(payload_candidate):
                    continue
                payload = payload_candidate
                resolved_ref = candidate_ref
                active_target = candidate_target
                maybe_node = candidate.get("node")
                resolved_node = maybe_node if isinstance(maybe_node, dict) else None
                recovered = True
                logger.debug(
                    "Recovered select by switching candidate profile=%s ref=%s",
                    profile,
                    candidate_ref,
                )
                break
            if not recovered and not _postcondition_ok(payload):
                if last_post_exc is not None:
                    raise last_post_exc
                raise ValueError(
                    "select operation completed but selected value did not match request"
                )
        if resolved_ref:
            payload["resolved_ref"] = resolved_ref
            self._remember_field_target_lock(
                profile=profile,
                target_id=active_target,
                operation="select",
                field_hint=field_hint,
                ref=resolved_ref,
            )
        if resolved_node:
            payload["resolved_node"] = resolved_node
        return payload

    async def _run_fill_fields(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return await self._fill_fields_engine.run_fill_fields(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            request=request,
        )

    async def _prefetch_fill_fields_refs(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> None:
        await self._fill_fields_engine.prefetch_fill_fields_refs(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            request=request,
        )

    async def _run_fill_fields_step_operation(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._fill_fields_engine.run_fill_fields_step_operation(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            step=step,
            operation=operation,
        )

    async def _run_act(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        text: Optional[str],
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        kind = _as_str(request.get("kind"))
        if not kind:
            raise ValueError("request.kind is required for act operation")
        kind = kind.lower()

        normalized_request = dict(request)
        req_target = (
            _as_str(normalized_request.get("target_id"))
            or _as_str(normalized_request.get("targetId"))
        )
        active_target = req_target or target_id
        if active_target and not req_target:
            normalized_request["target_id"] = active_target
        if selector and not _as_str(normalized_request.get("selector")):
            normalized_request["selector"] = selector
        if ref and not _as_str(normalized_request.get("ref")):
            normalized_request["ref"] = ref
        if text is not None and _as_str(normalized_request.get("text")) is None:
            normalized_request["text"] = text
        if kind in {"navigate", "open"} and _as_str(normalized_request.get("url")) is None:
            target_url = (
                _as_str(normalized_request.get("target_url"))
                or _as_str(normalized_request.get("targetUrl"))
            )
            if target_url:
                normalized_request["url"] = target_url

        resolved_target = (
            _as_str(normalized_request.get("target_id"))
            or _as_str(normalized_request.get("targetId"))
            or active_target
        )

        try:
            return await self._run_fill_fields_step_operation(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=resolved_target,
                step=normalized_request,
                operation=kind,
            )
        except ValueError as exc:
            message = str(exc)
            if message.startswith("fill_fields unsupported step operation:"):
                raise ValueError(f"Unsupported act kind: {kind}") from exc
            if message == "target_id is required for close operation":
                raise ValueError("target_id is required for act:close") from exc
            if message == "fill_fields step evaluate requires script/fn":
                raise ValueError("request.script/fn is required for act:evaluate") from exc
            raise
