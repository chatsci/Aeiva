"""Fill-fields orchestration engine for BrowserService."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
from typing import Any, Callable, Dict, Optional

from .element_matching import (
    _find_confirm_target_from_nodes,
    _find_select_target_from_nodes,
    _find_type_target_from_nodes,
    _is_stale_target_error,
)
from .fill_fields_step_ops import FillFieldsStepOpsMixin
from .logging_utils import _log_browser_event

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


@dataclass
class _FillFieldsRunContext:
    profile: str
    headless: bool
    timeout_ms: int
    continue_on_error: bool
    steps: list[Any]
    active_target: Optional[str]
    deduplicate_repeats: bool
    max_retries_per_step: int
    retry_delay_ms: int
    default_step_timeout_ms: int
    field_ref_cache: Dict[str, str] = field(default_factory=dict)
    cached_confirm_ref: Optional[str] = None
    previous_signature: Optional[tuple[Any, ...]] = None
    results: list[Dict[str, Any]] = field(default_factory=list)
    deduplicated_steps: int = 0
    retry_count: int = 0


class FillFieldsEngine(FillFieldsStepOpsMixin):
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
        context = await self._prepare_fill_fields_context(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            request=request,
        )
        await self._execute_fill_fields_steps(context)
        return self._aggregate_fill_fields_result(context)

    async def _prepare_fill_fields_context(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> _FillFieldsRunContext:
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

        context = _FillFieldsRunContext(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            continue_on_error=continue_on_error,
            steps=steps,
            active_target=target_id,
            deduplicate_repeats=self._h.as_bool(payload_req.get("deduplicate_repeats"), default=True),
            max_retries_per_step=max_retries_per_step,
            retry_delay_ms=retry_delay_ms,
            default_step_timeout_ms=default_step_timeout_ms,
        )

        if self._h.as_bool(payload_req.get("prefetch_refs"), default=True):
            prefetch = await self.prefetch_fill_fields_refs(
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=context.active_target,
                steps=steps,
            )
            prefetch_refs = prefetch.get("refs")
            if isinstance(prefetch_refs, dict):
                for key, value in prefetch_refs.items():
                    clean_key = str(key).strip().casefold()
                    clean_ref = self._h.as_str(value)
                    if clean_key and clean_ref:
                        context.field_ref_cache[clean_key] = clean_ref
            prefetch_target = self._h.as_str(prefetch.get("target_id"))
            if prefetch_target and not context.active_target:
                context.active_target = prefetch_target
            prefetched_confirm_ref = self._h.as_str(prefetch.get("confirm_ref"))
            if prefetched_confirm_ref:
                context.cached_confirm_ref = prefetched_confirm_ref
        return context

    async def _execute_fill_fields_steps(
        self,
        context: _FillFieldsRunContext,
    ) -> None:
        for index, step in enumerate(context.steps):
            if not isinstance(step, dict):
                raise ValueError(f"fill_fields step {index} must be an object")
            op = self._h.extract_operation_name(step)
            if not op:
                raise ValueError(f"fill_fields step {index} missing operation")
            signature = self._h.build_fill_fields_step_signature(step=step, operation=op)
            if context.deduplicate_repeats and signature == context.previous_signature:
                context.deduplicated_steps += 1
                context.results.append(
                    {
                        "index": index,
                        "operation": op,
                        "success": True,
                        "skipped": True,
                        "reason": "deduplicated_repeat",
                        "target_id": context.active_target,
                    }
                )
                continue
            context.previous_signature = signature
            step_field_key = self._h.build_fill_fields_field_key(step)
            used_cached_ref = False
            used_cached_confirm_ref = False
            if (
                step_field_key
                and op in {"type", "fill", "set_number", "set_date", "select", "choose_option"}
                and not self._h.as_str(step.get("selector"))
                and not self._h.as_str(step.get("ref"))
            ):
                cached_ref = context.field_ref_cache.get(step_field_key)
                if cached_ref:
                    step = dict(step)
                    step["ref"] = cached_ref
                    used_cached_ref = True
            if op in {"confirm", "submit"} and context.cached_confirm_ref:
                if not self._h.as_str(step.get("selector")) and not self._h.as_str(step.get("ref")):
                    step = dict(step)
                    step["ref"] = context.cached_confirm_ref
                    used_cached_confirm_ref = True
            if op == "set_date" and self._h.as_bool(step.get("confirm"), default=False) and context.cached_confirm_ref:
                if not self._h.as_str(step.get("confirm_selector")) and not self._h.as_str(step.get("confirm_ref")):
                    step = dict(step)
                    step["confirm_ref"] = context.cached_confirm_ref
                    used_cached_confirm_ref = True
            step_timeout_ms = self._h.normalize_timeout(
                self._h.coalesce(
                    self._h.as_int(step.get("timeout_ms")),
                    self._h.as_int(step.get("timeout")),
                    context.default_step_timeout_ms,
                )
            )

            try:
                step_payload = await self.run_fill_fields_step_operation(
                    profile=context.profile,
                    headless=context.headless,
                    timeout_ms=step_timeout_ms,
                    target_id=context.active_target,
                    step=step,
                    operation=op,
                )
                retried = False
            except Exception as exc:
                _log_browser_event(
                    logger,
                    level=logging.DEBUG,
                    event="fill_step_failed",
                    index=index,
                    op=op,
                    profile=context.profile,
                    error=exc,
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
                    context.field_ref_cache.pop(step_field_key, None)
                    retry_step = dict(step)
                    retry_step.pop("ref", None)
                    retry_step.pop("selector", None)
                    try:
                        step_payload = await self.run_fill_fields_step_operation(
                            profile=context.profile,
                            headless=context.headless,
                            timeout_ms=step_timeout_ms,
                            target_id=context.active_target,
                            step=retry_step,
                            operation=op,
                        )
                        _log_browser_event(
                            logger,
                            level=logging.DEBUG,
                            event="fill_step_recovered_stale_cached_ref",
                            index=index,
                            op=op,
                            profile=context.profile,
                        )
                        context.retry_count += 1
                        retried = True
                        recovered = True
                    except Exception as retry_exc:
                        exc = retry_exc
                if not recovered and used_cached_confirm_ref and _is_stale_target_error(exc):
                    context.cached_confirm_ref = None
                    retry_step = dict(step)
                    retry_step.pop("ref", None)
                    retry_step.pop("confirm_ref", None)
                    retry_step.pop("confirm_selector", None)
                    try:
                        step_payload = await self.run_fill_fields_step_operation(
                            profile=context.profile,
                            headless=context.headless,
                            timeout_ms=step_timeout_ms,
                            target_id=context.active_target,
                            step=retry_step,
                            operation=op,
                        )
                        _log_browser_event(
                            logger,
                            level=logging.DEBUG,
                            event="fill_step_recovered_stale_confirm_ref",
                            index=index,
                            op=op,
                            profile=context.profile,
                        )
                        context.retry_count += 1
                        retried = True
                        recovered = True
                    except Exception as retry_exc:
                        exc = retry_exc
                if (
                    not recovered
                    and context.max_retries_per_step > 0
                    and self._is_transient_step_error(exc)
                ):
                    last_exc: Exception = exc
                    for retry_index in range(context.max_retries_per_step):
                        if context.retry_delay_ms > 0:
                            # Lightweight linear backoff to let UI/network settle.
                            await asyncio.sleep(
                                (context.retry_delay_ms * (retry_index + 1)) / 1000.0
                            )
                        try:
                            step_payload = await self.run_fill_fields_step_operation(
                                profile=context.profile,
                                headless=context.headless,
                                timeout_ms=step_timeout_ms,
                                target_id=context.active_target,
                                step=step,
                                operation=op,
                            )
                            _log_browser_event(
                                logger,
                                level=logging.DEBUG,
                                event="fill_step_transient_retry_recovered",
                                index=index,
                                op=op,
                                profile=context.profile,
                                attempt=retry_index + 1,
                            )
                            context.retry_count += 1
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
                    context.results.append(failure)
                    if not context.continue_on_error:
                        raise
                    continue

            context.active_target = self._h.as_str(step_payload.get("target_id")) or context.active_target
            resolved_ref = self._h.as_str(step_payload.get("resolved_ref"))
            field_resolved_ref = self._h.as_str(step_payload.get("field_resolved_ref")) or resolved_ref
            if step_field_key and field_resolved_ref and op not in {"confirm", "submit"}:
                context.field_ref_cache[step_field_key] = field_resolved_ref
            confirm_resolved_ref = self._h.as_str(step_payload.get("confirm_resolved_ref"))
            if confirm_resolved_ref:
                context.cached_confirm_ref = confirm_resolved_ref
            elif op in {"confirm", "submit"} and resolved_ref:
                context.cached_confirm_ref = resolved_ref
            result_row: Dict[str, Any] = {
                "index": index,
                "operation": op,
                "success": True,
                "target_id": context.active_target,
            }
            if retried:
                result_row["retried"] = True
            context.results.append(result_row)
            _log_browser_event(
                logger,
                level=logging.DEBUG,
                event="fill_step_success",
                index=index,
                op=op,
                profile=context.profile,
                target_id=context.active_target,
                retried=retried,
            )

    @staticmethod
    def _aggregate_fill_fields_result(
        context: _FillFieldsRunContext,
    ) -> Dict[str, Any]:
        success_count = sum(1 for item in context.results if bool(item.get("success")))
        error_count = len(context.results) - success_count
        return {
            "fill_fields": True,
            "target_id": context.active_target,
            "steps": context.results,
            "step_count": len(context.results),
            "success_count": success_count,
            "error_count": error_count,
            "had_errors": error_count > 0,
            "deduplicated_steps": context.deduplicated_steps,
            "retry_count": context.retry_count,
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
