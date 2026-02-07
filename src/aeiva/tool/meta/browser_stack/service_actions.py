"""Action execution mixin for BrowserService."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from .logging_utils import _log_browser_event
from .service_actions_input import BrowserServiceInputActionsMixin
from .service_constants import DEFAULT_SCROLL_RECOVERY_CLICK_TIMEOUT_MS
from .service_runtime_ops import BrowserServiceRuntimeOpsMixin
from .service_utils import (
    _as_bool,
    _as_int,
    _as_str,
    _coalesce,
)

if TYPE_CHECKING:
    from .browser_service import _ExecuteContext

logger = logging.getLogger(__name__)


class BrowserServiceActionsMixin(BrowserServiceInputActionsMixin, BrowserServiceRuntimeOpsMixin):
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
                    _log_browser_event(
                        logger,
                        level=logging.DEBUG,
                        event="click_candidate_recovered",
                        profile=profile,
                        ref=candidate_ref,
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
