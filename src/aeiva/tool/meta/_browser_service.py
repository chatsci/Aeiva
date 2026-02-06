"""
Browser V2 service facade.

This file keeps tool-level orchestration separate from the runtime implementation.
"""

from __future__ import annotations

import base64
from urllib.parse import quote_plus
from typing import Any, Dict, Optional

from ._browser_runtime import BrowserSessionManager, DEFAULT_TIMEOUT_MS


class BrowserService:
    """Facade that maps browser tool operations onto runtime/session primitives."""

    SUPPORTED_OPERATIONS = {
        "status",
        "start",
        "stop",
        "profiles",
        "tabs",
        "open",
        "open_tab",
        "focus",
        "close",
        "close_tab",
        "navigate",
        "back",
        "forward",
        "reload",
        "click",
        "type",
        "press",
        "hover",
        "select",
        "drag",
        "scroll",
        "upload",
        "wait",
        "evaluate",
        "snapshot",
        "act",
        "screenshot",
        "pdf",
        "get_text",
        "get_html",
        "console",
        "errors",
        "network",
        "request",
        "search",
    }

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self._sessions = session_manager or BrowserSessionManager()

    async def execute(
        self,
        *,
        operation: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        query: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_MS,
        headless: bool = True,
        profile: str = "default",
        target_id: Optional[str] = None,
        ref: Optional[str] = None,
        request: Optional[Dict[str, Any]] = None,
        full_page: bool = False,
        image_type: str = "png",
        limit: int = 80,
    ) -> Dict[str, Any]:
        op = (operation or "").strip().lower()
        timeout_ms = _normalize_timeout(timeout)
        profile_name = (profile or "default").strip() or "default"
        effective_headless = await self._effective_headless(profile_name, headless)

        try:
            if op == "request":
                return await self._request(
                    url=url,
                    method=method,
                    headers=headers,
                    body=body,
                    timeout_ms=timeout_ms,
                )
            if op == "search":
                return await self._search(
                    query=query or text,
                    profile=profile_name,
                    headless=effective_headless,
                    timeout_ms=timeout_ms,
                    target_id=target_id,
                )

            if op == "start":
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.status(),
                )
                return self._ok(**payload)

            if op == "stop":
                stopped = await self._sessions.stop_session(profile_name)
                return self._ok(stopped=stopped, profile=profile_name)

            if op == "status":
                session = await self._sessions.get_session(profile_name)
                if session is None:
                    return self._ok(
                        running=False,
                        profile=profile_name,
                        headless=headless,
                        tab_count=0,
                        last_target_id=None,
                    )
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=session.headless,
                    create=False,
                    fn=lambda runtime: runtime.status(),
                )
                return self._ok(**payload)

            if op == "profiles":
                profiles = await self._sessions.list_profiles()
                return self._ok(profiles=profiles)

            if op == "tabs":
                session = await self._sessions.get_session(profile_name)
                if session is None:
                    return self._ok(profile=profile_name, tabs=[])
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=session.headless,
                    create=False,
                    fn=lambda runtime: runtime.list_tabs(),
                )
                return self._ok(profile=profile_name, tabs=payload)

            if op in {"open", "open_tab"}:
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.open_tab(url=(url or "about:blank"), timeout_ms=timeout_ms),
                )
                return self._ok(**payload)

            if op == "focus":
                focus_target = target_id or _as_str((request or {}).get("target_id")) or _as_str((request or {}).get("targetId"))
                if not focus_target:
                    return self._err("target_id required for focus operation")
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=headless,
                    create=False,
                    fn=lambda runtime: runtime.focus_tab(target_id=focus_target),
                )
                return self._ok(**payload)

            if op in {"close", "close_tab"}:
                close_target = (
                    target_id
                    or (request or {}).get("target_id")
                    or (request or {}).get("targetId")
                )
                if not close_target:
                    return self._err("target_id required for close operation")
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=headless,
                    create=False,
                    fn=lambda runtime: runtime.close_tab(target_id=str(close_target)),
                )
                return self._ok(**payload)

            if op == "navigate":
                if not url:
                    return self._err("URL required for navigate operation")
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.navigate(
                        url=url,
                        timeout_ms=timeout_ms,
                        target_id=target_id,
                    ),
                )
                return self._ok(**payload)

            if op == "back":
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.back(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                    ),
                )
                return self._ok(**payload)

            if op == "forward":
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.forward(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                    ),
                )
                return self._ok(**payload)

            if op == "reload":
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.reload(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                    ),
                )
                return self._ok(**payload)

            if op == "click":
                payload = await self._run_click(
                    profile=profile_name,
                    headless=effective_headless,
                    timeout_ms=timeout_ms,
                    target_id=target_id,
                    selector=selector,
                    ref=ref,
                    url=url,
                    request=request,
                )
                return self._ok(**payload)

            if op == "type":
                payload = await self._run_type(
                    profile=profile_name,
                    headless=effective_headless,
                    timeout_ms=timeout_ms,
                    target_id=target_id,
                    selector=selector,
                    ref=ref,
                    text=text,
                    url=url,
                    request=request,
                )
                return self._ok(**payload)

            if op == "press":
                key = str((request or {}).get("key") or text or "").strip()
                if not key:
                    return self._err("key required for press operation")
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.press(
                        key=key,
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                    ),
                )
                return self._ok(**payload)

            if op == "hover":
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.hover(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        selector=selector,
                        ref=ref,
                    ),
                )
                return self._ok(**payload)

            if op == "select":
                values = _normalize_values((request or {}).get("values"))
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.select(
                        values=values,
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        selector=selector,
                        ref=ref,
                    ),
                )
                return self._ok(**payload)

            if op == "drag":
                drag_req = request or {}
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.drag(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        start_selector=_as_str(drag_req.get("start_selector"))
                        or _as_str(drag_req.get("startSelector")),
                        start_ref=_as_str(drag_req.get("start_ref")) or _as_str(drag_req.get("startRef")),
                        end_selector=_as_str(drag_req.get("end_selector"))
                        or _as_str(drag_req.get("endSelector")),
                        end_ref=_as_str(drag_req.get("end_ref")) or _as_str(drag_req.get("endRef")),
                    ),
                )
                return self._ok(**payload)

            if op == "scroll":
                scroll_req = request or {}
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.scroll(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        selector=selector or _as_str(scroll_req.get("selector")),
                        ref=ref or _as_str(scroll_req.get("ref")),
                        delta_x=_coalesce(
                            _as_int(scroll_req.get("delta_x")),
                            _as_int(scroll_req.get("deltaX")),
                            0,
                        ),
                        delta_y=_coalesce(
                            _as_int(scroll_req.get("delta_y")),
                            _as_int(scroll_req.get("deltaY")),
                            800,
                        ),
                    ),
                )
                return self._ok(**payload)

            if op == "upload":
                upload_req = request or {}
                paths = _normalize_paths(upload_req.get("paths"))
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.upload(
                        paths=paths,
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        selector=selector or _as_str(upload_req.get("selector")),
                        ref=ref or _as_str(upload_req.get("ref")),
                    ),
                )
                return self._ok(**payload)

            if op == "wait":
                wait_req = request or {}
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.wait(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        selector=selector or _as_str(wait_req.get("selector")),
                        text=_as_str(wait_req.get("text")),
                        text_gone=_as_str(wait_req.get("text_gone"))
                        or _as_str(wait_req.get("textGone")),
                        url_contains=_as_str(wait_req.get("url_contains"))
                        or _as_str(wait_req.get("url")),
                        time_ms=_coalesce(
                            _as_int(wait_req.get("time_ms")),
                            _as_int(wait_req.get("timeMs")),
                        ),
                        load_state=_as_str(wait_req.get("load_state"))
                        or _as_str(wait_req.get("loadState")),
                    ),
                )
                return self._ok(**payload)

            if op == "evaluate":
                script = _as_str((request or {}).get("script")) or _as_str((request or {}).get("fn"))
                if not script:
                    return self._err("script/fn required for evaluate operation")
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.evaluate(
                        script=script,
                        target_id=target_id,
                        selector=selector,
                        ref=ref,
                    ),
                )
                return self._ok(**payload)

            if op == "snapshot":
                snapshot_limit = max(1, min(_as_int((request or {}).get("limit")) or limit, 200))
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.snapshot(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        limit=snapshot_limit,
                    ),
                )
                return self._ok(**payload)

            if op == "act":
                action_req = request or {}
                payload = await self._run_act(
                    profile=profile_name,
                    headless=effective_headless,
                    timeout_ms=timeout_ms,
                    target_id=target_id,
                    selector=selector,
                    ref=ref,
                    text=text,
                    request=action_req,
                )
                return self._ok(**payload)

            if op == "screenshot":
                img_type = (
                    _as_str((request or {}).get("type"))
                    or _as_str((request or {}).get("image_type"))
                    or image_type
                )
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.screenshot(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        full_page=bool((request or {}).get("full_page") or full_page),
                        image_type="jpeg" if str(img_type).lower() == "jpeg" else "png",
                        selector=selector,
                        ref=ref,
                    ),
                )
                image_bytes = payload.pop("screenshot")
                payload["screenshot"] = base64.b64encode(image_bytes).decode("utf-8")
                payload["format"] = "base64"
                return self._ok(**payload)

            if op == "pdf":
                pdf_req = request or {}
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.pdf(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        scale=_coalesce(_as_float(pdf_req.get("scale")), 1.0),
                        print_background=_as_bool(pdf_req.get("print_background"), default=True),
                    ),
                )
                pdf_bytes = payload.pop("pdf")
                payload["pdf"] = base64.b64encode(pdf_bytes).decode("utf-8")
                payload["format"] = "base64"
                return self._ok(**payload)

            if op == "get_text":
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.get_text(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        selector=selector,
                        ref=ref,
                    ),
                )
                return self._ok(**payload)

            if op == "get_html":
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=effective_headless,
                    create=True,
                    fn=lambda runtime: runtime.get_html(
                        target_id=target_id,
                        timeout_ms=timeout_ms,
                        selector=selector,
                        ref=ref,
                    ),
                )
                return self._ok(**payload)

            if op == "console":
                session = await self._sessions.get_session(profile_name)
                if session is None:
                    return self._ok(target_id=None, entries=[])
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=session.headless,
                    create=False,
                    fn=lambda runtime: runtime.get_console(
                        target_id=target_id,
                        limit=max(1, min(limit, 500)),
                    ),
                )
                return self._ok(**payload)

            if op == "errors":
                session = await self._sessions.get_session(profile_name)
                if session is None:
                    return self._ok(target_id=None, entries=[])
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=session.headless,
                    create=False,
                    fn=lambda runtime: runtime.get_errors(
                        target_id=target_id,
                        limit=max(1, min(limit, 500)),
                    ),
                )
                return self._ok(**payload)

            if op == "network":
                session = await self._sessions.get_session(profile_name)
                if session is None:
                    return self._ok(target_id=None, entries=[])
                payload = await self._sessions.run_with_session(
                    profile=profile_name,
                    headless=session.headless,
                    create=False,
                    fn=lambda runtime: runtime.get_network(
                        target_id=target_id,
                        limit=max(1, min(limit, 500)),
                    ),
                )
                return self._ok(**payload)

            return self._err(
                f"Unknown operation: {operation}",
                code="unknown_operation",
                details={"supported_operations": sorted(self.SUPPORTED_OPERATIONS)},
            )
        except ValueError as exc:
            return self._err(str(exc), code="invalid_request")
        except Exception as exc:
            message = str(exc)
            launch_details = _classify_launch_failure(message)
            if launch_details is not None:
                return self._err(message, code="launch_blocked", details=launch_details)
            return self._err(message, code="runtime_error")

    async def _effective_headless(self, profile: str, requested: bool) -> bool:
        session = await self._sessions.get_session(profile)
        if session is not None:
            return session.headless
        return bool(requested)

    async def _run_click(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        url: Optional[str],
        request: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        click_req = request or {}
        active_target = target_id
        if url:
            nav = await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.navigate(
                    url=url,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                ),
            )
            active_target = nav.get("target_id")

        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.click(
                target_id=active_target,
                timeout_ms=timeout_ms,
                selector=selector or _as_str(click_req.get("selector")),
                ref=ref or _as_str(click_req.get("ref")),
                double_click=bool(click_req.get("double_click") or click_req.get("doubleClick")),
                button=_as_str(click_req.get("button")) or "left",
            ),
        )

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
        active_target = target_id
        if url:
            nav = await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.navigate(
                    url=url,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                ),
            )
            active_target = nav.get("target_id")

        payload_text = _as_str(type_req.get("text"))
        if payload_text is None:
            payload_text = text
        if payload_text is None:
            raise ValueError("Text required for type operation")

        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.type_text(
                text=payload_text,
                target_id=active_target,
                timeout_ms=timeout_ms,
                selector=selector or _as_str(type_req.get("selector")),
                ref=ref or _as_str(type_req.get("ref")),
                submit=bool(type_req.get("submit")),
                slowly=bool(type_req.get("slowly")),
            ),
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

        req_target = _as_str(request.get("target_id")) or _as_str(request.get("targetId"))
        active_target = req_target or target_id
        req_selector = _as_str(request.get("selector")) or selector
        req_ref = _as_str(request.get("ref")) or ref
        req_text = _as_str(request.get("text")) or text

        if kind == "click":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.click(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    selector=req_selector,
                    ref=req_ref,
                    double_click=bool(request.get("double_click") or request.get("doubleClick")),
                    button=_as_str(request.get("button")) or "left",
                ),
            )

        if kind in {"type", "fill"}:
            if req_text is None:
                raise ValueError("request.text is required for act:type")
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.type_text(
                    text=req_text,
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    selector=req_selector,
                    ref=req_ref,
                    submit=bool(request.get("submit")),
                    slowly=bool(request.get("slowly")),
                ),
            )

        if kind == "press":
            key = _as_str(request.get("key")) or req_text
            if not key:
                raise ValueError("request.key is required for act:press")
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.press(
                    key=key,
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                ),
            )

        if kind == "hover":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.hover(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    selector=req_selector,
                    ref=req_ref,
                ),
            )

        if kind == "select":
            values = _normalize_values(request.get("values"))
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.select(
                    values=values,
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    selector=req_selector,
                    ref=req_ref,
                ),
            )

        if kind == "drag":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.drag(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    start_selector=_as_str(request.get("start_selector"))
                    or _as_str(request.get("startSelector")),
                    start_ref=_as_str(request.get("start_ref")) or _as_str(request.get("startRef")),
                    end_selector=_as_str(request.get("end_selector"))
                    or _as_str(request.get("endSelector")),
                    end_ref=_as_str(request.get("end_ref")) or _as_str(request.get("endRef")),
                ),
            )

        if kind == "scroll":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.scroll(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    selector=req_selector,
                    ref=req_ref,
                    delta_x=_coalesce(
                        _as_int(request.get("delta_x")),
                        _as_int(request.get("deltaX")),
                        0,
                    ),
                    delta_y=_coalesce(
                        _as_int(request.get("delta_y")),
                        _as_int(request.get("deltaY")),
                        800,
                    ),
                ),
            )

        if kind == "upload":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.upload(
                    paths=_normalize_paths(request.get("paths")),
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    selector=req_selector,
                    ref=req_ref,
                ),
            )

        if kind == "wait":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.wait(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                    selector=req_selector,
                    text=_as_str(request.get("text")),
                    text_gone=_as_str(request.get("text_gone"))
                    or _as_str(request.get("textGone")),
                    url_contains=_as_str(request.get("url_contains"))
                    or _as_str(request.get("url")),
                    time_ms=_coalesce(
                        _as_int(request.get("time_ms")),
                        _as_int(request.get("timeMs")),
                    ),
                    load_state=_as_str(request.get("load_state"))
                    or _as_str(request.get("loadState")),
                ),
            )

        if kind == "evaluate":
            script = _as_str(request.get("script")) or _as_str(request.get("fn"))
            if not script:
                raise ValueError("request.script/fn is required for act:evaluate")
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.evaluate(
                    script=script,
                    target_id=active_target,
                    selector=req_selector,
                    ref=req_ref,
                ),
            )

        if kind == "navigate":
            nav_url = _as_str(request.get("url")) or _as_str(request.get("target_url"))
            if not nav_url:
                raise ValueError("request.url is required for act:navigate")
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.navigate(
                    url=nav_url,
                    timeout_ms=timeout_ms,
                    target_id=active_target,
                ),
            )

        if kind == "reload":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.reload(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                ),
            )

        if kind == "back":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.back(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                ),
            )

        if kind == "forward":
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.forward(
                    target_id=active_target,
                    timeout_ms=timeout_ms,
                ),
            )

        if kind == "close":
            if not active_target:
                raise ValueError("target_id is required for act:close")
            return await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=False,
                fn=lambda runtime: runtime.close_tab(target_id=active_target),
            )

        raise ValueError(f"Unsupported act kind: {kind}")

    async def _request(
        self,
        *,
        url: Optional[str],
        method: str,
        headers: Optional[Dict[str, str]],
        body: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        if not url:
            return self._err("URL required for request operation")

        import aiohttp

        timeout_sec = timeout_ms / 1000
        async with aiohttp.ClientSession() as session:
            kwargs: Dict[str, Any] = {"timeout": aiohttp.ClientTimeout(total=timeout_sec)}
            if headers:
                kwargs["headers"] = headers
            if body and method.upper() in {"POST", "PUT", "PATCH"}:
                kwargs["data"] = body

            async with session.request(method.upper(), url, **kwargs) as response:
                try:
                    response_body = await response.text()
                except Exception:
                    raw = await response.read()
                    response_body = raw.decode("utf-8", errors="replace")
                return self._ok(
                    status=response.status,
                    headers=dict(response.headers),
                    body=response_body,
                )

    async def _search(
        self,
        *,
        query: Optional[str],
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
    ) -> Dict[str, Any]:
        clean = (query or "").strip()
        if not clean:
            return self._err("Query required for search operation")

        # Browser search should act on a real page for interactive user requests.
        search_url = f"https://www.google.com/search?q={quote_plus(clean)}"
        try:
            payload = await self._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.navigate(
                    url=search_url,
                    timeout_ms=timeout_ms,
                    target_id=target_id,
                ),
            )
            if _looks_like_google_sorry(payload):
                bing_url = f"https://www.bing.com/search?q={quote_plus(clean)}"
                payload = await self._sessions.run_with_session(
                    profile=profile,
                    headless=headless,
                    create=True,
                    fn=lambda runtime: runtime.navigate(
                        url=bing_url,
                        timeout_ms=timeout_ms,
                        target_id=payload.get("target_id") or target_id,
                    ),
                )
                return self._ok(
                    query=clean,
                    engine="bing",
                    note="Google presented anti-bot verification; switched to Bing.",
                    **payload,
                )
            return self._ok(query=clean, engine="google", **payload)
        except Exception:
            # Fall back to text search so this operation still returns useful output
            # when browser navigation is blocked.
            pass

        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return self._ok(
                query=clean,
                results=[],
                search_url=search_url,
                note=(
                    "Browser navigation and duckduckgo-search are unavailable; "
                    "open search_url manually."
                ),
            )

        with DDGS() as ddgs:
            results = list(ddgs.text(clean, max_results=10))
        return self._ok(query=clean, results=results, engine="duckduckgo")

    @staticmethod
    def _ok(**payload: Any) -> Dict[str, Any]:
        out = {"success": True, "error": None}
        out.update(payload)
        return out

    @staticmethod
    def _err(message: str, *, code: str = "browser_error", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": False,
            "error": message,
            "error_code": code,
        }
        if details:
            payload["error_details"] = details
        return payload


def _normalize_timeout(timeout: Optional[int]) -> int:
    if timeout is None:
        return DEFAULT_TIMEOUT_MS
    try:
        value = int(timeout)
    except Exception:
        return DEFAULT_TIMEOUT_MS
    return max(1, value)


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _normalize_values(value: Any) -> list[str]:
    if value is None:
        raise ValueError("values are required for select operation")
    if isinstance(value, (list, tuple)):
        items = [str(v) for v in value if str(v).strip()]
        if items:
            return items
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    raise ValueError("values are required for select operation")


def _normalize_paths(value: Any) -> list[str]:
    if value is None:
        raise ValueError("paths are required for upload operation")
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, (list, tuple)):
        paths = [str(v).strip() for v in value if str(v).strip()]
        if paths:
            return paths
    raise ValueError("paths are required for upload operation")


def _classify_launch_failure(message: str) -> Optional[Dict[str, Any]]:
    text = (message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    if (
        "playwright" not in lowered
        and "browsertype.launch" not in lowered
        and "failed to launch browser automation" not in lowered
        and "mach_port_rendezvous" not in lowered
        and "subprocess support is unavailable" not in lowered
        and "get_child_watcher" not in lowered
    ):
        return None

    details: Dict[str, Any] = {"category": "launch_failure"}
    if "subprocess support is unavailable" in lowered or "get_child_watcher" in lowered:
        details["category"] = "event_loop_policy"
        details["hint"] = (
            "The runtime event-loop policy does not support subprocess launch for the "
            "active loop. Restart Aeiva and avoid loop-policy overrides (e.g. uvloop) "
            "for the gateway loop."
        )
        return details

    if "mach_port_rendezvous" in lowered or "permission denied (1100)" in lowered:
        details["category"] = "sandbox_permission"
        details["hint"] = (
            "Browser launch was blocked by macOS sandbox permissions. "
            "Run Aeiva outside the sandboxed environment, or route browser execution "
            "to an unsandboxed host bridge."
        )
        return details

    if "executable doesn't exist" in lowered or "executable not found" in lowered:
        details["category"] = "browser_missing"
        details["hint"] = "Install browser binaries: playwright install chromium"
        return details

    if "playwright is not installed" in lowered:
        details["category"] = "dependency_missing"
        details["hint"] = "Install tool extras: pip install -e '.[tools]'"
        return details

    return details


def _looks_like_google_sorry(payload: Dict[str, Any]) -> bool:
    url = _as_str(payload.get("url")) or ""
    title = (_as_str(payload.get("title")) or "").lower()
    lowered_url = url.lower()
    if "google.com/sorry" in lowered_url:
        return True
    if "/sorry/" in lowered_url and "google." in lowered_url:
        return True
    if "unusual traffic" in title:
        return True
    return False


_BROWSER_SERVICE: Optional[BrowserService] = None


def get_browser_service() -> BrowserService:
    global _BROWSER_SERVICE
    if _BROWSER_SERVICE is None:
        _BROWSER_SERVICE = BrowserService()
    return _BROWSER_SERVICE


def set_browser_service(service: Optional[BrowserService]) -> None:
    global _BROWSER_SERVICE
    _BROWSER_SERVICE = service
