"""Content extraction and observability mixin for PlaywrightRuntime."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .logging_utils import _log_browser_event
from .runtime_common import _coerce_bool, _safe_title
from .runtime_snapshot_script import _SNAPSHOT_JS

logger = logging.getLogger(__name__)


class RuntimeContentMixin:
    async def screenshot(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        full_page: bool,
        image_type: str,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        image_kind = "jpeg" if image_type == "jpeg" else "png"

        if selector or ref:
            primary_selector, fallback_selector = self._resolve_selector(
                target_id=resolved_target, selector=selector, ref=ref
            )
            locator = await self._wait_for_locator(
                page,
                primary_selector,
                timeout_ms,
                fallback_selector=fallback_selector,
            )
            data = await locator.screenshot(type=image_kind, timeout=timeout_ms)
        else:
            data = await page.screenshot(
                full_page=full_page,
                type=image_kind,
                timeout=timeout_ms,
            )

        return {
            "target_id": resolved_target,
            "url": _safe_title(getattr(page, "url", "")),
            "screenshot": data,
            "mime_type": f"image/{image_kind}",
        }

    async def pdf(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        scale: float = 1.0,
        print_background: bool = True,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        pdf_bytes = await page.pdf(
            print_background=bool(print_background),
            scale=max(0.1, min(float(scale), 2.0)),
            timeout=timeout_ms,
        )
        return {
            "target_id": resolved_target,
            "url": _safe_title(getattr(page, "url", "")),
            "pdf": pdf_bytes,
            "mime_type": "application/pdf",
        }

    async def get_text(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        if selector or ref:
            primary_selector, fallback_selector = self._resolve_selector(
                target_id=resolved_target, selector=selector, ref=ref
            )
            locator = await self._wait_for_locator(
                page,
                primary_selector,
                timeout_ms,
                fallback_selector=fallback_selector,
            )
            text = await locator.inner_text(timeout=timeout_ms)
        else:
            text = await page.inner_text("body", timeout=timeout_ms)
        return {
            "target_id": resolved_target,
            "url": _safe_title(getattr(page, "url", "")),
            "text": text,
        }

    async def get_html(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        if selector or ref:
            primary_selector, fallback_selector = self._resolve_selector(
                target_id=resolved_target, selector=selector, ref=ref
            )
            locator = await self._wait_for_locator(
                page,
                primary_selector,
                timeout_ms,
                fallback_selector=fallback_selector,
            )
            html = await locator.inner_html(timeout=timeout_ms)
        else:
            html = await page.content()
        return {
            "target_id": resolved_target,
            "url": _safe_title(getattr(page, "url", "")),
            "html": html,
        }

    async def snapshot(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        limit: int,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)

        max_items = max(1, min(int(limit), 200))
        raw_scoped_nodes: List[tuple[str, List[Dict[str, Any]]]] = []
        contexts = [("main", page)]
        for idx, frame in enumerate(self._iter_locator_contexts(page)[1:], start=1):
            contexts.append((f"frame-{idx}", frame))

        collected = 0
        for scope, context in contexts:
            remaining = max_items - collected
            if remaining <= 0:
                break
            nodes = await self._snapshot_nodes_for_context(context, remaining)
            if not nodes:
                continue
            raw_scoped_nodes.append((scope, nodes))
            collected += len(nodes)

        ref_map: Dict[str, Dict[str, Any]] = {}
        nodes: List[Dict[str, Any]] = []
        lines: List[str] = []

        emitted = 0
        for scope, scoped_nodes in raw_scoped_nodes:
            for node in scoped_nodes:
                if not isinstance(node, dict):
                    continue
                emitted += 1
                raw_ref = _safe_title(node.get("ref")).strip() or f"e{emitted}"
                ref = raw_ref if scope == "main" else f"{scope}:{raw_ref}"
                selector = _safe_title(node.get("selector")).strip()
                fallback_selector = _safe_title(node.get("fallback_selector")).strip()
                if not selector and not fallback_selector:
                    continue

                role = _safe_title(node.get("role")).strip() or _safe_title(node.get("tag")).strip()
                tag = _safe_title(node.get("tag")).strip()
                name = _safe_title(node.get("name")).strip()
                text_value = _safe_title(node.get("text")).strip()
                aria_label = _safe_title(node.get("aria_label")).strip()
                placeholder = _safe_title(node.get("placeholder")).strip()
                value = _safe_title(node.get("value")).strip()
                aria_valuenow = _safe_title(node.get("aria_valuenow")).strip()
                input_type = _safe_title(node.get("input_type")).strip()
                dom_id = _safe_title(node.get("dom_id")).strip()
                name_attr = _safe_title(node.get("name_attr")).strip()
                label_text = _safe_title(node.get("label_text")).strip()
                readonly = _coerce_bool(node.get("readonly"))
                disabled = _coerce_bool(node.get("disabled"))

                ref_map[ref] = {
                    "selector": selector or fallback_selector,
                    "fallback_selector": fallback_selector or None,
                    "tag": tag,
                    "role": role,
                    "name": name,
                    "text": text_value,
                    "aria_label": aria_label,
                    "placeholder": placeholder,
                    "value": value,
                    "aria_valuenow": aria_valuenow,
                    "input_type": input_type,
                    "dom_id": dom_id,
                    "name_attr": name_attr,
                    "label_text": label_text,
                    "readonly": readonly,
                    "disabled": disabled,
                    "scope": scope,
                }

                nodes.append(
                    {
                        "ref": ref,
                        "scope": scope,
                        "tag": tag,
                        "role": role,
                        "name": name,
                        "text": text_value,
                        "aria_label": aria_label,
                        "placeholder": placeholder,
                        "value": value,
                        "aria_valuenow": aria_valuenow,
                        "input_type": input_type,
                        "dom_id": dom_id,
                        "name_attr": name_attr,
                        "label_text": label_text,
                        "readonly": readonly,
                        "disabled": disabled,
                        "selector": selector or fallback_selector,
                        "fallback_selector": fallback_selector or None,
                    }
                )

                line_label = name or label_text or name_attr or text_value or value or selector or fallback_selector
                scope_prefix = "" if scope == "main" else f"{scope} "
                lines.append(f"{ref} [{scope_prefix}{role or 'node'}] {line_label}".strip())

        tab = self._tab_states.get(resolved_target)
        if tab is not None:
            tab.refs = ref_map

        return {
            "target_id": resolved_target,
            "url": _safe_title(getattr(page, "url", "")),
            "nodes": nodes,
            "snapshot": "\n".join(lines),
        }

    async def _snapshot_nodes_for_context(
        self,
        context: Any,
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            nodes = await context.evaluate(_SNAPSHOT_JS, {"limit": max(1, min(limit, 200))})
        except Exception as exc:
            _log_browser_event(
                logger,
                level=logging.DEBUG,
                event="snapshot_context_eval_failed",
                error=exc,
            )
            return []
        if not isinstance(nodes, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for node in nodes:
            if isinstance(node, dict):
                normalized.append(node)
        return normalized

    async def get_console(
        self,
        *,
        target_id: Optional[str],
        limit: int,
    ) -> Dict[str, Any]:
        tab = await self._resolve_tab_state(target_id=target_id, create=False)
        if tab is None:
            return {"entries": [], "target_id": None}
        items = list(tab.events.console)[-max(1, int(limit)) :]
        return {"target_id": tab.target_id, "entries": items}

    async def get_errors(
        self,
        *,
        target_id: Optional[str],
        limit: int,
    ) -> Dict[str, Any]:
        tab = await self._resolve_tab_state(target_id=target_id, create=False)
        if tab is None:
            return {"entries": [], "target_id": None}
        items = list(tab.events.errors)[-max(1, int(limit)) :]
        return {"target_id": tab.target_id, "entries": items}

    async def get_network(
        self,
        *,
        target_id: Optional[str],
        limit: int,
    ) -> Dict[str, Any]:
        tab = await self._resolve_tab_state(target_id=target_id, create=False)
        if tab is None:
            return {"entries": [], "target_id": None}
        items = list(tab.events.network)[-max(1, int(limit)) :]
        return {"target_id": tab.target_id, "entries": items}
