"""Fill-fields orchestration engine for BrowserService."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Callable, Dict, Optional

from .element_matching import (
    _find_confirm_target_from_nodes,
    _find_select_target_from_nodes,
    _find_type_target_from_nodes,
    _is_stale_target_error,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FillFieldsHelpers:
    as_str: Callable[[Any], Optional[str]]
    as_int: Callable[[Any], Optional[int]]
    as_bool: Callable[..., bool]
    coalesce: Callable[..., Any]
    normalize_timeout: Callable[[Optional[int]], int]
    normalize_values: Callable[[Any], list[str]]
    normalize_paths: Callable[[Any], tuple[str, ...]]
    extract_operation_name: Callable[[Dict[str, Any]], str]
    expand_fill_fields_shorthand: Callable[..., list[Dict[str, Any]]]
    build_fill_fields_field_key: Callable[[Dict[str, Any]], Optional[str]]
    build_fill_fields_step_signature: Callable[..., tuple[Any, ...]]


class FillFieldsEngine:
    def __init__(
        self,
        *,
        service: Any,
        helpers: FillFieldsHelpers,
        default_fill_step_timeout_ms: int,
        default_snapshot_resolve_limit: int,
        supported_step_operations: tuple[str, ...],
    ) -> None:
        self._service = service
        self._h = helpers
        self._default_fill_step_timeout_ms = default_fill_step_timeout_ms
        self._default_snapshot_resolve_limit = default_snapshot_resolve_limit
        self._supported_step_operations = supported_step_operations

    @staticmethod
    def _is_transient_step_error(exc: Exception) -> bool:
        message = str(exc or "").casefold()
        if not message:
            return False
        if _is_stale_target_error(exc):
            return True
        transient_tokens = (
            "transient",
            "timeout",
            "timed out",
            "detached",
            "intercept",
            "temporar",
            "connection reset",
            "connection aborted",
            "target closed",
            "navigation failed",
            "net::",
            "econn",
        )
        return any(token in message for token in transient_tokens)

    async def run_fill_fields(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        payload_req = request or {}
        raw_steps = payload_req.get("steps")
        submit_requested = self._h.as_bool(payload_req.get("submit"), default=False)
        confirm_date = self._h.as_bool(payload_req.get("confirm_date"), default=submit_requested)
        if (not isinstance(raw_steps, list) or not raw_steps) and isinstance(payload_req.get("fields"), dict):
            raw_steps = self._h.expand_fill_fields_shorthand(
                fields=payload_req.get("fields") or {},
                submit=submit_requested,
                confirm_date=confirm_date,
            )
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("fill_fields requires a non-empty request.steps list")

        stop_on_error_override = payload_req.get("stop_on_error")
        if stop_on_error_override is None:
            continue_on_error = self._h.as_bool(payload_req.get("continue_on_error"), default=False)
        else:
            continue_on_error = not self._h.as_bool(stop_on_error_override, default=True)
        max_steps = max(1, min(self._h.as_int(payload_req.get("max_steps")) or 12, 30))
        steps = raw_steps[:max_steps]
        results: list[Dict[str, Any]] = []
        active_target = target_id
        field_ref_cache: Dict[str, str] = {}
        cached_confirm_ref: Optional[str] = None
        deduplicate_repeats = self._h.as_bool(payload_req.get("deduplicate_repeats"), default=True)
        deduplicated_steps = 0
        retry_count = 0
        max_retries_per_step = max(
            0,
            min(self._h.as_int(payload_req.get("max_retries_per_step")) or 0, 3),
        )
        retry_delay_ms = max(
            0,
            min(self._h.as_int(payload_req.get("retry_delay_ms")) or 120, 1200),
        )
        requested_default_step_timeout = self._h.coalesce(
            self._h.as_int(payload_req.get("default_step_timeout_ms")),
            self._h.as_int(payload_req.get("default_step_timeout")),
        )
        if requested_default_step_timeout is None:
            default_step_timeout_ms = self._h.normalize_timeout(min(timeout_ms, self._default_fill_step_timeout_ms))
        else:
            default_step_timeout_ms = self._h.normalize_timeout(
                min(timeout_ms, int(requested_default_step_timeout))
            )
        previous_signature: Optional[tuple[Any, ...]] = None
        if self._h.as_bool(payload_req.get("prefetch_refs"), default=True):
            prefetch = await self.prefetch_fill_fields_refs(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=active_target,
                steps=steps,
            )
            prefetch_refs = prefetch.get("refs")
            if isinstance(prefetch_refs, dict):
                for key, value in prefetch_refs.items():
                    clean_key = str(key).strip().casefold()
                    clean_ref = self._h.as_str(value)
                    if clean_key and clean_ref:
                        field_ref_cache[clean_key] = clean_ref
            prefetch_target = self._h.as_str(prefetch.get("target_id"))
            if prefetch_target and not active_target:
                active_target = prefetch_target
            prefetched_confirm_ref = self._h.as_str(prefetch.get("confirm_ref"))
            if prefetched_confirm_ref:
                cached_confirm_ref = prefetched_confirm_ref

        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError(f"fill_fields step {index} must be an object")
            op = self._h.extract_operation_name(step)
            if not op:
                raise ValueError(f"fill_fields step {index} missing operation")
            signature = self._h.build_fill_fields_step_signature(step=step, operation=op)
            if deduplicate_repeats and signature == previous_signature:
                deduplicated_steps += 1
                results.append(
                    {
                        "index": index,
                        "operation": op,
                        "success": True,
                        "skipped": True,
                        "reason": "deduplicated_repeat",
                        "target_id": active_target,
                    }
                )
                continue
            previous_signature = signature
            step_field_key = self._h.build_fill_fields_field_key(step)
            used_cached_ref = False
            used_cached_confirm_ref = False
            if (
                step_field_key
                and op in {"type", "fill", "set_number", "set_date", "select", "choose_option"}
                and not self._h.as_str(step.get("selector"))
                and not self._h.as_str(step.get("ref"))
            ):
                cached_ref = field_ref_cache.get(step_field_key)
                if cached_ref:
                    step = dict(step)
                    step["ref"] = cached_ref
                    used_cached_ref = True
            if op in {"confirm", "submit"} and cached_confirm_ref:
                if not self._h.as_str(step.get("selector")) and not self._h.as_str(step.get("ref")):
                    step = dict(step)
                    step["ref"] = cached_confirm_ref
                    used_cached_confirm_ref = True
            if op == "set_date" and self._h.as_bool(step.get("confirm"), default=False) and cached_confirm_ref:
                if not self._h.as_str(step.get("confirm_selector")) and not self._h.as_str(step.get("confirm_ref")):
                    step = dict(step)
                    step["confirm_ref"] = cached_confirm_ref
                    used_cached_confirm_ref = True
            step_timeout_ms = self._h.normalize_timeout(
                self._h.coalesce(
                    self._h.as_int(step.get("timeout_ms")),
                    self._h.as_int(step.get("timeout")),
                    default_step_timeout_ms,
                )
            )

            try:
                step_payload = await self.run_fill_fields_step_operation(
                    profile=profile,
                    headless=headless,
                    timeout_ms=step_timeout_ms,
                    target_id=active_target,
                    step=step,
                    operation=op,
                )
                retried = False
            except Exception as exc:
                logger.debug(
                    "fill_fields step failed index=%s op=%s profile=%s error=%s",
                    index,
                    op,
                    profile,
                    exc,
                )
                recovered = False
                if used_cached_ref and step_field_key and op in {
                    "type",
                    "fill",
                    "set_number",
                    "set_date",
                    "select",
                    "choose_option",
                } and _is_stale_target_error(exc):
                    field_ref_cache.pop(step_field_key, None)
                    retry_step = dict(step)
                    retry_step.pop("ref", None)
                    retry_step.pop("selector", None)
                    try:
                        step_payload = await self.run_fill_fields_step_operation(
                            profile=profile,
                            headless=headless,
                            timeout_ms=step_timeout_ms,
                            target_id=active_target,
                            step=retry_step,
                            operation=op,
                        )
                        logger.debug(
                            "fill_fields recovered stale cached ref index=%s op=%s profile=%s",
                            index,
                            op,
                            profile,
                        )
                        retry_count += 1
                        retried = True
                        recovered = True
                    except Exception as retry_exc:
                        exc = retry_exc
                if not recovered and used_cached_confirm_ref and _is_stale_target_error(exc):
                    cached_confirm_ref = None
                    retry_step = dict(step)
                    retry_step.pop("ref", None)
                    retry_step.pop("confirm_ref", None)
                    retry_step.pop("confirm_selector", None)
                    try:
                        step_payload = await self.run_fill_fields_step_operation(
                            profile=profile,
                            headless=headless,
                            timeout_ms=step_timeout_ms,
                            target_id=active_target,
                            step=retry_step,
                            operation=op,
                        )
                        logger.debug(
                            "fill_fields recovered stale confirm ref index=%s op=%s profile=%s",
                            index,
                            op,
                            profile,
                        )
                        retry_count += 1
                        retried = True
                        recovered = True
                    except Exception as retry_exc:
                        exc = retry_exc
                if (
                    not recovered
                    and max_retries_per_step > 0
                    and self._is_transient_step_error(exc)
                ):
                    last_exc: Exception = exc
                    for retry_index in range(max_retries_per_step):
                        if retry_delay_ms > 0:
                            # Lightweight linear backoff to let UI/network settle.
                            await asyncio.sleep(
                                (retry_delay_ms * (retry_index + 1)) / 1000.0
                            )
                        try:
                            step_payload = await self.run_fill_fields_step_operation(
                                profile=profile,
                                headless=headless,
                                timeout_ms=step_timeout_ms,
                                target_id=active_target,
                                step=step,
                                operation=op,
                            )
                            logger.debug(
                                "fill_fields transient retry recovered index=%s op=%s profile=%s attempt=%s",
                                index,
                                op,
                                profile,
                                retry_index + 1,
                            )
                            retry_count += 1
                            retried = True
                            recovered = True
                            break
                        except Exception as retry_exc:
                            last_exc = retry_exc
                    exc = last_exc
                if not recovered:
                    failure = {
                        "index": index,
                        "operation": op,
                        "success": False,
                        "error": str(exc),
                    }
                    if "unsupported step operation" in str(exc):
                        failure["supported_step_operations"] = list(self._supported_step_operations)
                    results.append(failure)
                    if not continue_on_error:
                        raise
                    continue

            active_target = self._h.as_str(step_payload.get("target_id")) or active_target
            resolved_ref = self._h.as_str(step_payload.get("resolved_ref"))
            field_resolved_ref = self._h.as_str(step_payload.get("field_resolved_ref")) or resolved_ref
            if step_field_key and field_resolved_ref and op not in {"confirm", "submit"}:
                field_ref_cache[step_field_key] = field_resolved_ref
            confirm_resolved_ref = self._h.as_str(step_payload.get("confirm_resolved_ref"))
            if confirm_resolved_ref:
                cached_confirm_ref = confirm_resolved_ref
            elif op in {"confirm", "submit"} and resolved_ref:
                cached_confirm_ref = resolved_ref
            result_row: Dict[str, Any] = {
                "index": index,
                "operation": op,
                "success": True,
                "target_id": active_target,
            }
            if retried:
                result_row["retried"] = True
            results.append(result_row)
            logger.debug(
                "fill_fields step success index=%s op=%s profile=%s target_id=%s retried=%s",
                index,
                op,
                profile,
                active_target,
                retried,
            )

        success_count = sum(1 for item in results if bool(item.get("success")))
        error_count = len(results) - success_count
        return {
            "fill_fields": True,
            "target_id": active_target,
            "steps": results,
            "step_count": len(results),
            "success_count": success_count,
            "error_count": error_count,
            "had_errors": error_count > 0,
            "deduplicated_steps": deduplicated_steps,
            "retry_count": retry_count,
        }

    async def prefetch_fill_fields_refs(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        steps: list[Any],
    ) -> Dict[str, Any]:
        descriptors: list[tuple[str, str, Dict[str, Any]]] = []
        seen_fields: set[str] = set()
        need_confirm_ref = False

        for raw_step in steps:
            if not isinstance(raw_step, dict):
                continue
            op = self._h.extract_operation_name(raw_step)
            if op in {"confirm", "submit"}:
                if not self._h.as_str(raw_step.get("selector")) and not self._h.as_str(raw_step.get("ref")):
                    need_confirm_ref = True
            if op == "set_date" and self._h.as_bool(raw_step.get("confirm"), default=False):
                if not self._h.as_str(raw_step.get("confirm_selector")) and not self._h.as_str(raw_step.get("confirm_ref")):
                    need_confirm_ref = True
            if op not in {"type", "fill", "set_number", "set_date", "select", "choose_option"}:
                continue
            if self._h.as_str(raw_step.get("selector")) or self._h.as_str(raw_step.get("ref")):
                continue
            field_key = self._h.build_fill_fields_field_key(raw_step)
            if not field_key or field_key in seen_fields:
                continue
            seen_fields.add(field_key)
            descriptors.append((field_key, op, raw_step))

        if not descriptors and not need_confirm_ref:
            return {"refs": {}, "target_id": target_id}

        nodes, resolved_target_id = await self._service._snapshot_nodes_for_resolution(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            limit=self._default_snapshot_resolve_limit,
        )
        if nodes is None:
            return {"refs": {}, "target_id": target_id}

        refs: Dict[str, str] = {}
        for field_key, op, step in descriptors:
            field_hint = (
                self._h.as_str(step.get("field"))
                or self._h.as_str(step.get("label"))
                or self._h.as_str(step.get("name"))
            )
            matched: Optional[Dict[str, Any]]
            if op in {"type", "fill", "set_number", "set_date"}:
                value_text = self._h.as_str(step.get("value")) or self._h.as_str(step.get("text")) or field_key
                matched = _find_type_target_from_nodes(
                    nodes,
                    value_text=value_text,
                    field_hint=field_hint,
                )
            else:
                raw_values = step.get("values")
                if raw_values is None and step.get("value") is not None:
                    raw_values = step.get("value")
                try:
                    values = self._h.normalize_values(raw_values)
                except Exception:
                    values = []
                matched = _find_select_target_from_nodes(
                    nodes,
                    values=values,
                    field_hint=field_hint,
                )

            ref = self._h.as_str((matched or {}).get("ref"))
            if ref:
                refs[field_key] = ref

        return {
            "refs": refs,
            "confirm_ref": self._h.as_str((_find_confirm_target_from_nodes(nodes) or {}).get("ref")),
            "target_id": resolved_target_id or target_id,
        }

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
