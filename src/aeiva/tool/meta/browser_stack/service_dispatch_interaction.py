"""Interaction dispatch branches for BrowserService."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from .service_utils import (
    _as_int,
    _as_str,
    _coalesce,
    _normalize_paths,
)

if TYPE_CHECKING:
    from .service import _ExecuteContext


class BrowserServiceDispatchInteractionMixin:
    async def _execute_interaction_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        result = await self._execute_interaction_form_ops(ctx)
        if result is not None:
            return result
        return await self._execute_interaction_runtime_ops(ctx)

    async def _execute_interaction_form_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        handler = {
            "click": self._interaction_click,
            "confirm": self._interaction_confirm,
            "submit": self._interaction_submit,
            "type": self._interaction_type,
            "press": self._interaction_press,
            "hover": self._interaction_hover,
            "set_number": self._interaction_set_value,
            "set_date": self._interaction_set_value,
            "fill_fields": self._interaction_fill_fields,
            "workflow": self._interaction_fill_fields,
            "select": self._interaction_select,
            "choose_option": self._interaction_select,
        }.get(ctx.op)
        if handler is None:
            return None
        return await handler(ctx)

    async def _execute_interaction_runtime_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        handler = {
            "drag": self._interaction_drag,
            "scroll": self._interaction_scroll,
            "upload": self._interaction_upload,
            "wait": self._interaction_wait,
            "evaluate": self._interaction_evaluate,
            "snapshot": self._interaction_snapshot,
            "act": self._interaction_act,
        }.get(ctx.op)
        if handler is None:
            return None
        return await handler(ctx)

    async def _interaction_click(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._run_click(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            text=ctx.text,
            url=ctx.url,
            request=ctx.request,
        )
        return self._ok(**payload)

    async def _interaction_confirm(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._run_confirm(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            text=ctx.text,
            request=ctx.request,
        )
        return self._ok(**payload)

    async def _interaction_submit(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._run_confirm(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            text=_as_str(ctx.request.get("text")) or ctx.text,
            request=ctx.request,
        )
        payload["submit_action"] = True
        return self._ok(**payload)

    async def _interaction_type(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._run_type(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            text=ctx.text,
            url=ctx.url,
            request=ctx.request,
        )
        return self._ok(**payload)

    async def _interaction_press(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        key = str(ctx.request.get("key") or ctx.text or "").strip()
        if not key:
            return self._err("key required for press operation")
        payload = await self._runtime_press(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            key=key,
        )
        return self._ok(**payload)

    async def _interaction_hover(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._runtime_hover(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
        )
        return self._ok(**payload)

    async def _interaction_set_value(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        return await self._run_set_operation(ctx=ctx, operation=ctx.op)

    async def _interaction_fill_fields(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._run_fill_fields(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            request=ctx.request,
        )
        if ctx.op == "workflow":
            payload["workflow"] = True
        return self._ok(**payload)

    async def _interaction_select(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._run_select(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            request=ctx.request,
        )
        return self._ok(**payload)

    async def _interaction_drag(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._runtime_drag(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            start_selector=_as_str(ctx.request.get("start_selector"))
            or _as_str(ctx.request.get("startSelector")),
            start_ref=_as_str(ctx.request.get("start_ref"))
            or _as_str(ctx.request.get("startRef")),
            end_selector=_as_str(ctx.request.get("end_selector"))
            or _as_str(ctx.request.get("endSelector")),
            end_ref=_as_str(ctx.request.get("end_ref")) or _as_str(ctx.request.get("endRef")),
        )
        return self._ok(**payload)

    async def _interaction_scroll(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        return await self._run_scroll_action(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            request=ctx.request,
        )

    async def _interaction_upload(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._runtime_upload(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            paths=_normalize_paths(ctx.request.get("paths")),
            selector=ctx.selector or _as_str(ctx.request.get("selector")),
            ref=ctx.ref or _as_str(ctx.request.get("ref")),
        )
        return self._ok(**payload)

    async def _interaction_wait(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        payload = await self._runtime_wait(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector or _as_str(ctx.request.get("selector")),
            selector_state=_as_str(ctx.request.get("selector_state"))
            or _as_str(ctx.request.get("selectorState"))
            or _as_str(ctx.request.get("state")),
            text=_as_str(ctx.request.get("text")),
            text_gone=_as_str(ctx.request.get("text_gone"))
            or _as_str(ctx.request.get("textGone")),
            url_contains=_as_str(ctx.request.get("url_contains"))
            or _as_str(ctx.request.get("url")),
            time_ms=_coalesce(
                _as_int(ctx.request.get("time_ms")),
                _as_int(ctx.request.get("timeMs")),
            ),
            load_state=_as_str(ctx.request.get("load_state"))
            or _as_str(ctx.request.get("loadState")),
        )
        return self._ok(**payload)

    async def _interaction_evaluate(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        policy_error = self._evaluate_policy_error(ctx.profile)
        if policy_error is not None:
            return policy_error
        script = _as_str(ctx.request.get("script")) or _as_str(ctx.request.get("fn"))
        if not script:
            return self._err("script/fn required for evaluate operation")
        payload = await self._run_evaluate_action(
            profile=ctx.profile,
            headless=ctx.headless,
            script=script,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
        )
        return self._ok(**payload)

    async def _interaction_snapshot(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        snapshot_limit = max(1, min(_as_int(ctx.request.get("limit")) or ctx.limit, 200))
        payload = await self._runtime_snapshot(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            limit=snapshot_limit,
        )
        return self._ok(**payload)

    async def _interaction_act(self, ctx: _ExecuteContext) -> Dict[str, Any]:
        kind = (_as_str(ctx.request.get("kind")) or "").lower()
        if kind == "evaluate":
            policy_error = self._evaluate_policy_error(ctx.profile)
            if policy_error is not None:
                return policy_error
        if kind == "scroll":
            return await self._run_scroll_action(
                profile=ctx.profile,
                headless=ctx.headless,
                timeout_ms=ctx.timeout_ms,
                target_id=ctx.target_id,
                selector=ctx.selector,
                ref=ctx.ref,
                request=ctx.request,
            )
        payload = await self._run_act(
            profile=ctx.profile,
            headless=ctx.headless,
            timeout_ms=ctx.timeout_ms,
            target_id=ctx.target_id,
            selector=ctx.selector,
            ref=ctx.ref,
            text=ctx.text,
            request=ctx.request,
        )
        return self._ok(**payload)
