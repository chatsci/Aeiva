"""Input-oriented action mixin for BrowserService."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from .element_matching import _is_stale_target_error
from .logging_utils import _log_browser_event
from .service_utils import (
    _as_bool,
    _as_str,
    _coalesce,
    _normalize_values,
)

logger = logging.getLogger(__name__)


class BrowserServiceInputActionsMixin:
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
                _log_browser_event(
                    logger,
                    level=logging.DEBUG,
                    event="type_candidate_recovered",
                    profile=profile,
                    ref=candidate_ref,
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
                    _log_browser_event(
                        logger,
                        level=logging.DEBUG,
                        event="type_slow_retry_recovered",
                        profile=profile,
                        ref=resolved_ref,
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
                _log_browser_event(
                    logger,
                    level=logging.DEBUG,
                    event="select_candidate_recovered",
                    profile=profile,
                    ref=candidate_ref,
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
