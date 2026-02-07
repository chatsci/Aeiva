"""State and tab-lifecycle mixin for PlaywrightRuntime."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .runtime_common import (
    DEFAULT_POST_GOTO_SETTLE_MS,
    TabState,
    _normalize_timeout,
    _now_iso,
    _parse_int_env,
    _read_attr,
    _safe_title,
)


class RuntimeStateMixin:
    async def _ensure_started(self) -> None:
        if not self._started:
            await self.start()

    async def _sync_known_pages(self) -> None:
        if self._context is None:
            return
        for page in self._context.pages:
            self._register_page(page)

    def _on_page_created(self, page: Any) -> None:
        self._register_page(page)

    def _register_page(self, page: Any) -> str:
        page_key = id(page)
        known = self._page_to_tab.get(page_key)
        if known:
            return known

        target_id = f"tab-{self._next_tab_id}"
        self._next_tab_id += 1
        tab = TabState(target_id=target_id, page=page)
        self._tab_states[target_id] = tab
        self._page_to_tab[page_key] = target_id
        self._last_target_id = target_id

        page.on("console", lambda msg, tid=target_id: self._record_console(tid, msg))
        page.on("pageerror", lambda err, tid=target_id: self._record_error(tid, err))
        page.on("request", lambda req, tid=target_id: self._record_network_request(tid, req))
        page.on("response", lambda resp, tid=target_id: self._record_network_response(tid, resp))
        page.on(
            "requestfailed",
            lambda req, tid=target_id: self._record_network_failed(tid, req),
        )
        page.on(
            "close",
            lambda tid=target_id, page_obj=page: self._unregister_page(tid, page_obj),
        )
        return target_id

    def _unregister_page(self, target_id: str, page: Any) -> None:
        self._tab_states.pop(target_id, None)
        self._page_to_tab.pop(id(page), None)
        if self._last_target_id == target_id:
            self._last_target_id = next(iter(self._tab_states.keys()), None)

    def _record_console(self, target_id: str, msg: Any) -> None:
        tab = self._tab_states.get(target_id)
        if tab is None:
            return
        location: Dict[str, Any] = {}
        try:
            location = msg.location() or {}
        except Exception:
            location = {}
        tab.events.console.append(
            {
                "timestamp": _now_iso(),
                "type": _safe_title(_read_attr(msg, "type")),
                "text": _safe_title(_read_attr(msg, "text")),
                "location": location,
            }
        )

    def _record_error(self, target_id: str, err: Any) -> None:
        tab = self._tab_states.get(target_id)
        if tab is None:
            return
        tab.events.errors.append(
            {
                "timestamp": _now_iso(),
                "message": _safe_title(getattr(err, "message", err)),
                "name": _safe_title(getattr(err, "name", "")),
            }
        )

    def _record_network_request(self, target_id: str, req: Any) -> None:
        tab = self._tab_states.get(target_id)
        if tab is None:
            return
        tab.events.network.append(
            {
                "timestamp": _now_iso(),
                "event": "request",
                "method": _safe_title(_read_attr(req, "method")),
                "url": _safe_title(_read_attr(req, "url")),
                "resource_type": _safe_title(_read_attr(req, "resource_type")),
            }
        )

    def _record_network_response(self, target_id: str, resp: Any) -> None:
        tab = self._tab_states.get(target_id)
        if tab is None:
            return
        request = _read_attr(resp, "request", None)
        req_url = _safe_title(_read_attr(request, "url"))
        tab.events.network.append(
            {
                "timestamp": _now_iso(),
                "event": "response",
                "url": req_url or _safe_title(_read_attr(resp, "url")),
                "status": int(_read_attr(resp, "status", 0) or 0),
                "ok": bool(_read_attr(resp, "ok", False)),
            }
        )

    def _record_network_failed(self, target_id: str, req: Any) -> None:
        tab = self._tab_states.get(target_id)
        if tab is None:
            return
        failure = _read_attr(req, "failure", None)
        tab.events.network.append(
            {
                "timestamp": _now_iso(),
                "event": "requestfailed",
                "method": _safe_title(_read_attr(req, "method")),
                "url": _safe_title(_read_attr(req, "url")),
                "error_text": _safe_title(_read_attr(failure, "error_text")),
            }
        )

    async def _resolve_page(
        self,
        *,
        target_id: Optional[str],
        create: bool,
    ) -> tuple[Any, str]:
        await self._ensure_started()
        await self._sync_known_pages()

        chosen_target = (target_id or "").strip()
        if chosen_target:
            tab = self._tab_states.get(chosen_target)
            if tab is None:
                raise ValueError(f"Unknown target_id: {chosen_target}")
            self._last_target_id = chosen_target
            return tab.page, chosen_target

        if self._last_target_id and self._last_target_id in self._tab_states:
            tab = self._tab_states[self._last_target_id]
            return tab.page, tab.target_id

        if self._tab_states:
            first_target = next(iter(self._tab_states.keys()))
            self._last_target_id = first_target
            tab = self._tab_states[first_target]
            return tab.page, tab.target_id

        if not create:
            raise ValueError("No active browser tab")

        page = await self._context.new_page()
        new_target = self._register_page(page)
        return page, new_target

    async def _resolve_tab_state(
        self,
        *,
        target_id: Optional[str],
        create: bool,
    ) -> Optional[TabState]:
        if not self._started:
            return None
        page, resolved_target = await self._resolve_page(target_id=target_id, create=create)
        _ = page
        return self._tab_states.get(resolved_target)

    async def _tab_payload(self, target_id: str) -> Dict[str, Any]:
        tab = self._tab_states.get(target_id)
        if tab is None:
            return {"target_id": target_id, "url": "", "title": ""}

        page = tab.page
        title = ""
        viewport_scroll = {"x": 0, "y": 0}
        try:
            title = await page.title()
        except Exception:
            title = ""
        try:
            viewport_scroll = await self._read_viewport_scroll(page)
        except Exception:
            viewport_scroll = {"x": 0, "y": 0}
        return {
            "target_id": target_id,
            "url": _safe_title(getattr(page, "url", "")),
            "title": _safe_title(title),
            "viewport_scroll": viewport_scroll,
        }

    async def _read_viewport_scroll(self, page: Any) -> Dict[str, int]:
        try:
            value = await page.evaluate(
                "() => ({x: Math.round(window.scrollX || 0), y: Math.round(window.scrollY || 0)})"
            )
        except Exception:
            return {"x": 0, "y": 0}
        if not isinstance(value, dict):
            return {"x": 0, "y": 0}
        return {
            "x": int(value.get("x") or 0),
            "y": int(value.get("y") or 0),
        }

    async def _goto(self, page: Any, url: str, timeout_ms: int) -> None:
        normalized_timeout = _normalize_timeout(timeout_ms)
        settle_timeout = min(
            normalized_timeout,
            _parse_int_env(
                "AEIVA_BROWSER_POST_GOTO_SETTLE_MS",
                DEFAULT_POST_GOTO_SETTLE_MS,
                50,
            ),
        )
        last_error: Optional[Exception] = None
        for _ in range(2):
            try:
                await page.goto(
                    url,
                    timeout=normalized_timeout,
                    wait_until="domcontentloaded",
                )
                # Many modern SPAs mount critical form widgets shortly after DOM ready.
                # Best-effort extra settle improves reliability without hard failing.
                try:
                    await page.wait_for_load_state(
                        "networkidle",
                        timeout=settle_timeout,
                    )
                except Exception:
                    pass
                return
            except Exception as exc:
                last_error = exc
                await page.wait_for_timeout(120)
        if last_error is not None:
            raise last_error
