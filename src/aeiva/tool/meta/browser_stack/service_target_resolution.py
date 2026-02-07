"""Target resolution helpers for BrowserService."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .element_matching import (
    _find_click_target_candidates_from_nodes,
    _find_click_target_from_nodes,
    _find_confirm_target_from_nodes,
    _find_select_target_candidates_from_nodes,
    _find_type_target_candidates_from_nodes,
)
from .service_constants import (
    DEFAULT_SNAPSHOT_RESOLVE_LIMIT,
    DEFAULT_SNAPSHOT_RESOLVE_TIMEOUT_MS,
)
from .service_utils import _as_str


class BrowserServiceTargetResolutionMixin:
    async def _snapshot_nodes_for_resolution(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        limit: int = DEFAULT_SNAPSHOT_RESOLVE_LIMIT,
    ) -> tuple[Optional[list[Any]], Optional[str]]:
        try:
            snapshot_payload = await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.snapshot(
                    target_id=target_id,
                    timeout_ms=min(timeout_ms, DEFAULT_SNAPSHOT_RESOLVE_TIMEOUT_MS),
                    limit=max(1, min(int(limit), 400)),
                ),
            )
        except Exception:
            return None, target_id

        resolved_target_id = _as_str(snapshot_payload.get("target_id")) or target_id
        nodes = snapshot_payload.get("nodes")
        if not isinstance(nodes, list):
            return None, resolved_target_id
        return nodes, resolved_target_id

    async def _resolve_target_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        matcher: Callable[[list[Any]], Optional[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        nodes, resolved_target_id = await self._snapshot_nodes_for_resolution(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
        )
        if not nodes:
            return None

        matched = matcher(nodes)
        if not matched:
            return None

        ref = _as_str(matched.get("ref"))
        if not ref:
            return None

        return {
            "target_id": resolved_target_id or target_id,
            "ref": ref,
            "node": matched,
        }

    async def _resolve_click_target_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        query_text: str,
    ) -> Optional[Dict[str, Any]]:
        clean_text = (query_text or "").strip()
        if not clean_text:
            return None
        return await self._resolve_target_from_snapshot(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            matcher=lambda nodes: _find_click_target_from_nodes(nodes, query_text=clean_text),
        )

    async def _resolve_click_targets_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        query_text: str,
        max_results: int = 3,
    ) -> list[Dict[str, Any]]:
        clean_text = (query_text or "").strip()
        if not clean_text:
            return []
        nodes, resolved_target_id = await self._snapshot_nodes_for_resolution(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
        )
        if not nodes:
            return []
        matched = _find_click_target_candidates_from_nodes(
            nodes,
            query_text=clean_text,
            max_results=max_results,
        )
        out: list[Dict[str, Any]] = []
        for item in matched:
            ref = _as_str(item.get("ref"))
            if not ref:
                continue
            out.append(
                {
                    "target_id": resolved_target_id or target_id,
                    "ref": ref,
                    "node": item,
                }
            )
        return out

    async def _resolve_confirm_target_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        query_text: Optional[str],
        context: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return await self._resolve_target_from_snapshot(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            matcher=lambda nodes: _find_confirm_target_from_nodes(
                nodes,
                preferred_text=query_text,
                context=context,
            ),
        )

    async def _resolve_type_target_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        value_text: str,
        field_hint: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        matches = await self._resolve_type_targets_from_snapshot(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            value_text=value_text,
            field_hint=field_hint,
            max_results=1,
        )
        return matches[0] if matches else None

    async def _resolve_type_targets_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        value_text: str,
        field_hint: Optional[str],
        max_results: int = 3,
    ) -> list[Dict[str, Any]]:
        nodes, resolved_target_id = await self._snapshot_nodes_for_resolution(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
        )
        if not nodes:
            return []
        matched = _find_type_target_candidates_from_nodes(
            nodes,
            value_text=value_text,
            field_hint=field_hint,
            max_results=max_results,
        )
        out: list[Dict[str, Any]] = []
        for item in matched:
            ref = _as_str(item.get("ref"))
            if not ref:
                continue
            out.append(
                {
                    "target_id": resolved_target_id or target_id,
                    "ref": ref,
                    "node": item,
                }
            )
        return out

    async def _resolve_select_target_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        values: list[str],
        field_hint: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        matches = await self._resolve_select_targets_from_snapshot(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            values=values,
            field_hint=field_hint,
            max_results=1,
        )
        return matches[0] if matches else None

    async def _resolve_select_targets_from_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        values: list[str],
        field_hint: Optional[str],
        max_results: int = 3,
    ) -> list[Dict[str, Any]]:
        nodes, resolved_target_id = await self._snapshot_nodes_for_resolution(
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
        )
        if not nodes:
            return []
        matched = _find_select_target_candidates_from_nodes(
            nodes,
            values=values,
            field_hint=field_hint,
            max_results=max_results,
        )
        out: list[Dict[str, Any]] = []
        for item in matched:
            ref = _as_str(item.get("ref"))
            if not ref:
                continue
            out.append(
                {
                    "target_id": resolved_target_id or target_id,
                    "ref": ref,
                    "node": item,
                }
            )
        return out
