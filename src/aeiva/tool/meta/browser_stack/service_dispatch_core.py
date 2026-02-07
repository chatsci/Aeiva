"""Core dispatch branches for BrowserService."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, Dict, Optional

from .service_utils import (
    _as_bool,
    _as_float,
    _as_int,
    _as_str,
    _coalesce,
)

if TYPE_CHECKING:
    from .service import _ExecuteContext


class BrowserServiceDispatchCoreMixin:
    async def _dispatch_execute(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        handlers = (
            self._execute_request_ops,
            self._execute_session_ops,
            self._execute_navigation_ops,
            self._execute_interaction_ops,
            self._execute_artifact_ops,
            self._execute_monitor_ops,
        )
        for handler in handlers:
            result = await handler(ctx)
            if result is not None:
                return result
        return None

    async def _execute_request_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        if ctx.op == "request":
            return await self._request(
                url=ctx.url,
                method=ctx.method,
                headers=ctx.headers,
                body=ctx.body,
                timeout_ms=ctx.timeout_ms,
            )
        if ctx.op == "search":
            return await self._search(
                query=ctx.query or ctx.text,
                profile=ctx.profile,
                headless=ctx.headless,
                timeout_ms=ctx.timeout_ms,
                target_id=ctx.target_id,
            )
        return None

    async def _execute_session_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        if ctx.op == "start":
            force_new_instance = _as_bool(
                _coalesce(
                    ctx.request.get("fresh"),
                    ctx.request.get("restart"),
                    ctx.request.get("new_instance"),
                    ctx.request.get("newInstance"),
                ),
                default=False,
            )
            if force_new_instance:
                await self._sessions.stop_session(ctx.profile)
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=ctx.headless,
                create=True,
                fn=lambda runtime: runtime.status(),
            )
            if force_new_instance:
                payload["fresh_start"] = True
            return self._ok(**payload)

        if ctx.op == "stop":
            stopped = await self._sessions.stop_session(ctx.profile)
            return self._ok(stopped=stopped, profile=ctx.profile)

        if ctx.op == "status":
            session = await self._sessions.get_session(ctx.profile)
            if session is None:
                return self._ok(
                    running=False,
                    profile=ctx.profile,
                    headless=ctx.requested_headless,
                    tab_count=0,
                    last_target_id=None,
                )
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=session.headless,
                create=False,
                fn=lambda runtime: runtime.status(),
            )
            return self._ok(**payload)

        if ctx.op == "profiles":
            profiles = await self._sessions.list_profiles()
            return self._ok(profiles=profiles)

        if ctx.op == "tabs":
            session = await self._sessions.get_session(ctx.profile)
            if session is None:
                return self._ok(profile=ctx.profile, tabs=[])
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=session.headless,
                create=False,
                fn=lambda runtime: runtime.list_tabs(),
            )
            return self._ok(profile=ctx.profile, tabs=payload)
        return None

    async def _execute_navigation_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        if ctx.op in {"open", "open_tab"}:
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=ctx.headless,
                create=True,
                fn=lambda runtime: runtime.open_tab(
                    url=(ctx.url or "about:blank"),
                    timeout_ms=ctx.timeout_ms,
                ),
            )
            return self._ok(**payload)

        if ctx.op == "focus":
            focus_target = (
                ctx.target_id
                or _as_str(ctx.request.get("target_id"))
                or _as_str(ctx.request.get("targetId"))
            )
            if not focus_target:
                return self._err("target_id required for focus operation")
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=ctx.requested_headless,
                create=False,
                fn=lambda runtime: runtime.focus_tab(target_id=focus_target),
            )
            return self._ok(**payload)

        if ctx.op in {"close", "close_tab"}:
            close_target = (
                ctx.target_id
                or ctx.request.get("target_id")
                or ctx.request.get("targetId")
            )
            if not close_target:
                return self._err("target_id required for close operation")
            payload = await self._runtime_close_tab(
                profile=ctx.profile,
                headless=ctx.requested_headless,
                target_id=str(close_target),
            )
            return self._ok(**payload)

        if ctx.op == "navigate":
            if not ctx.url:
                return self._err("URL required for navigate operation")
            payload = await self._runtime_navigate(
                profile=ctx.profile,
                headless=ctx.headless,
                timeout_ms=ctx.timeout_ms,
                target_id=ctx.target_id,
                url=ctx.url,
            )
            return self._ok(**payload)

        if ctx.op in {"back", "forward", "reload"}:
            payload = await self._runtime_history(
                profile=ctx.profile,
                headless=ctx.headless,
                timeout_ms=ctx.timeout_ms,
                target_id=ctx.target_id,
                operation=ctx.op,
            )
            return self._ok(**payload)
        return None

    async def _execute_artifact_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        if ctx.op == "screenshot":
            img_type = (
                _as_str(ctx.request.get("type"))
                or _as_str(ctx.request.get("image_type"))
                or ctx.image_type
            )
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=ctx.headless,
                create=True,
                fn=lambda runtime: runtime.screenshot(
                    target_id=ctx.target_id,
                    timeout_ms=ctx.timeout_ms,
                    full_page=bool(ctx.request.get("full_page") or ctx.full_page),
                    image_type="jpeg" if str(img_type).lower() == "jpeg" else "png",
                    selector=ctx.selector,
                    ref=ctx.ref,
                ),
            )
            image_bytes = payload.pop("screenshot")
            payload["screenshot"] = base64.b64encode(image_bytes).decode("utf-8")
            payload["format"] = "base64"
            return self._ok(**payload)

        if ctx.op == "pdf":
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=ctx.headless,
                create=True,
                fn=lambda runtime: runtime.pdf(
                    target_id=ctx.target_id,
                    timeout_ms=ctx.timeout_ms,
                    scale=_coalesce(_as_float(ctx.request.get("scale")), 1.0),
                    print_background=_as_bool(ctx.request.get("print_background"), default=True),
                ),
            )
            pdf_bytes = payload.pop("pdf")
            payload["pdf"] = base64.b64encode(pdf_bytes).decode("utf-8")
            payload["format"] = "base64"
            return self._ok(**payload)

        if ctx.op == "get_text":
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=ctx.headless,
                create=True,
                fn=lambda runtime: runtime.get_text(
                    target_id=ctx.target_id,
                    timeout_ms=ctx.timeout_ms,
                    selector=ctx.selector,
                    ref=ctx.ref,
                ),
            )
            return self._ok(**payload)

        if ctx.op == "get_html":
            payload = await self._sessions.run_with_session(
                profile=ctx.profile,
                headless=ctx.headless,
                create=True,
                fn=lambda runtime: runtime.get_html(
                    target_id=ctx.target_id,
                    timeout_ms=ctx.timeout_ms,
                    selector=ctx.selector,
                    ref=ctx.ref,
                ),
            )
            return self._ok(**payload)
        return None

    async def _execute_monitor_ops(self, ctx: _ExecuteContext) -> Optional[Dict[str, Any]]:
        monitor_ops = {
            "console": "get_console",
            "errors": "get_errors",
            "network": "get_network",
        }
        runtime_op = monitor_ops.get(ctx.op)
        if runtime_op is None:
            return None
        session = await self._sessions.get_session(ctx.profile)
        if session is None:
            return self._ok(target_id=None, entries=[])
        payload = await self._sessions.run_with_session(
            profile=ctx.profile,
            headless=session.headless,
            create=False,
            fn=lambda runtime: getattr(runtime, runtime_op)(
                target_id=ctx.target_id,
                limit=max(1, min(ctx.limit, 500)),
            ),
        )
        return self._ok(**payload)
