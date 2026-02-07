"""Step operation mixin for FillFieldsEngine."""

from __future__ import annotations

from typing import Any, Dict, Optional


class FillFieldsStepOpsMixin:
    async def run_fill_fields_step_operation(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        op = (operation or "").strip().lower()
        payload = await self._run_step_form_ops(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            step=step,
            operation=op,
        )
        if payload is not None:
            return payload
        payload = await self._run_step_runtime_ops(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            step=step,
            operation=op,
        )
        if payload is not None:
            return payload
        raise ValueError(f"fill_fields unsupported step operation: {op}")

    async def _run_step_form_ops(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Optional[Dict[str, Any]]:
        op = operation
        if op in {"type", "fill", "set_number", "set_date"}:
            return await self._fill_step_type_like(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=target_id,
                step=step,
                operation=op,
            )
        handler = {
            "select": self._fill_step_select_like,
            "choose_option": self._fill_step_select_like,
            "confirm": self._fill_step_confirm_like,
            "submit": self._fill_step_confirm_like,
            "click": self._fill_step_click_like,
        }.get(op)
        if handler is None:
            return None
        return await handler(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            step=step,
            operation=op,
        )

    async def _run_step_runtime_ops(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Optional[Dict[str, Any]]:
        op = operation
        if op in {"navigate", "open"}:
            return await self._fill_step_navigate_like(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=target_id,
                step=step,
                operation=op,
            )
        if op in {"back", "forward", "reload"}:
            return await self._fill_step_history_like(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=target_id,
                step=step,
                operation=op,
            )
        handler = {
            "search": self._fill_step_search_like,
            "snapshot": self._fill_step_snapshot_like,
            "press": self._fill_step_press_like,
            "hover": self._fill_step_hover_like,
            "drag": self._fill_step_drag_like,
            "upload": self._fill_step_upload_like,
            "scroll": self._fill_step_scroll_like,
            "wait": self._fill_step_wait_like,
            "evaluate": self._fill_step_evaluate_like,
            "close": self._fill_step_close_like,
        }.get(op)
        if handler is None:
            return None
        return await handler(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            step=step,
            operation=op,
        )

    async def _fill_step_type_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        value = self._h.as_str(step.get("value")) or self._h.as_str(step.get("text"))
        if value is None:
            raise ValueError(f"fill_fields step requires value/text for {operation}")
        type_req = dict(step)
        type_req["text"] = value
        if operation == "set_number" and not (
            self._h.as_str(type_req.get("field"))
            or self._h.as_str(type_req.get("label"))
            or self._h.as_str(type_req.get("name"))
        ):
            type_req["field"] = "number"
        if operation == "set_date" and not (
            self._h.as_str(type_req.get("field"))
            or self._h.as_str(type_req.get("label"))
            or self._h.as_str(type_req.get("name"))
        ):
            type_req["field"] = "date"
        payload = await self._service._run_type(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
            text=value,
            url=None,
            request=type_req,
        )
        if operation in {"set_number", "set_date"}:
            payload[operation] = True
        if operation != "set_date" or not self._h.as_bool(step.get("confirm"), default=False):
            return payload
        field_resolved_ref = self._h.as_str(payload.get("resolved_ref"))
        confirm_payload = await self._service._run_confirm(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=self._h.as_str(payload.get("target_id")) or target_id,
            selector=self._h.as_str(step.get("confirm_selector")),
            ref=self._h.as_str(step.get("confirm_ref")),
            text=self._h.as_str(step.get("confirm_text")) or self._h.as_str(step.get("text")),
            request=step,
        )
        confirm_resolved_ref = self._h.as_str(confirm_payload.get("resolved_ref"))
        payload.update(confirm_payload)
        if field_resolved_ref:
            payload["field_resolved_ref"] = field_resolved_ref
        if confirm_resolved_ref:
            payload["confirm_resolved_ref"] = confirm_resolved_ref
        return payload

    async def _fill_step_select_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._run_select(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
            request=step,
        )

    async def _fill_step_confirm_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        payload = await self._service._run_confirm(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
            text=self._h.as_str(step.get("text")),
            request=step,
        )
        confirm_resolved_ref = self._h.as_str(payload.get("resolved_ref"))
        if confirm_resolved_ref:
            payload["confirm_resolved_ref"] = confirm_resolved_ref
        if operation == "submit":
            payload["submit_action"] = True
        return payload

    async def _fill_step_click_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._run_click(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
            text=self._h.as_str(step.get("text")),
            url=self._h.as_str(step.get("url")),
            request=step,
        )

    async def _fill_step_navigate_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        nav_url = (
            self._h.as_str(step.get("url"))
            or self._h.as_str(step.get("target_url"))
            or self._h.as_str(step.get("targetUrl"))
            or self._h.as_str(step.get("value"))
            or self._h.as_str(step.get("text"))
        )
        if not nav_url:
            raise ValueError("fill_fields step navigate requires url/value/text")
        return await self._service._runtime_navigate(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            url=nav_url,
        )

    async def _fill_step_search_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        query_text = self._h.as_str(step.get("query")) or self._h.as_str(step.get("text")) or self._h.as_str(step.get("value"))
        if not query_text:
            raise ValueError("fill_fields step search requires query/text/value")
        payload = await self._service._search(
            query=query_text,
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
        )
        return self._unwrap_service_payload(payload=payload, fallback_error="search failed")

    async def _fill_step_history_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._runtime_history(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            operation=operation,
        )

    async def _fill_step_snapshot_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._runtime_snapshot(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            limit=max(1, min(self._h.as_int(step.get("limit")) or 120, 200)),
        )

    async def _fill_step_press_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        key = self._h.as_str(step.get("key")) or self._h.as_str(step.get("text"))
        if not key:
            raise ValueError("fill_fields step press requires key")
        return await self._service._runtime_press(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            key=key,
        )

    async def _fill_step_hover_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._runtime_hover(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
        )

    async def _fill_step_drag_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._runtime_drag(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            start_selector=self._h.as_str(step.get("start_selector"))
            or self._h.as_str(step.get("startSelector")),
            start_ref=self._h.as_str(step.get("start_ref")) or self._h.as_str(step.get("startRef")),
            end_selector=self._h.as_str(step.get("end_selector"))
            or self._h.as_str(step.get("endSelector")),
            end_ref=self._h.as_str(step.get("end_ref")) or self._h.as_str(step.get("endRef")),
        )

    async def _fill_step_upload_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._runtime_upload(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            paths=self._h.normalize_paths(step.get("paths")),
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
        )

    async def _fill_step_scroll_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        payload = await self._service._run_scroll_action(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
            request=step,
        )
        return self._unwrap_service_payload(payload=payload, fallback_error="scroll failed")

    async def _fill_step_wait_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        return await self._service._runtime_wait(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            selector_state=self._h.as_str(step.get("selector_state"))
            or self._h.as_str(step.get("selectorState"))
            or self._h.as_str(step.get("state")),
            text=self._h.as_str(step.get("text")),
            text_gone=self._h.as_str(step.get("text_gone"))
            or self._h.as_str(step.get("textGone")),
            url_contains=self._h.as_str(step.get("url_contains"))
            or self._h.as_str(step.get("urlContains"))
            or self._h.as_str(step.get("url")),
            time_ms=self._h.coalesce(
                self._h.as_int(step.get("time_ms")),
                self._h.as_int(step.get("timeMs")),
                self._h.as_int(step.get("time")),
            ),
            load_state=self._h.as_str(step.get("load_state"))
            or self._h.as_str(step.get("loadState")),
        )

    async def _fill_step_evaluate_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        policy_error = self._service._evaluate_policy_error(profile)
        if policy_error is not None:
            raise ValueError(str(policy_error.get("error") or "evaluate operation blocked by policy"))
        script = self._h.as_str(step.get("script")) or self._h.as_str(step.get("fn"))
        if not script:
            raise ValueError("fill_fields step evaluate requires script/fn")
        return await self._service._run_evaluate_action(
            profile=profile,
            headless=headless,
            script=script,
            target_id=target_id,
            selector=self._h.as_str(step.get("selector")),
            ref=self._h.as_str(step.get("ref")),
        )

    async def _fill_step_close_like(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        step: Dict[str, Any],
        operation: str,
    ) -> Dict[str, Any]:
        if not target_id:
            raise ValueError("target_id is required for close operation")
        return await self._service._runtime_close_tab(
            profile=profile,
            headless=headless,
            target_id=target_id,
        )

    def _unwrap_service_payload(
        self,
        *,
        payload: Dict[str, Any],
        fallback_error: str,
    ) -> Dict[str, Any]:
        if payload.get("success"):
            clean_payload = dict(payload)
            clean_payload.pop("success", None)
            clean_payload.pop("error", None)
            clean_payload.pop("error_code", None)
            clean_payload.pop("error_details", None)
            return clean_payload
        message = self._h.as_str(payload.get("error")) or fallback_error
        code = self._h.as_str(payload.get("error_code"))
        if code:
            raise ValueError(f"{message} (code: {code})")
        raise ValueError(message)
