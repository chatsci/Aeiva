"""Runtime and network operation mixin for BrowserService."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from .service_utils import _as_bool

logger = logging.getLogger(__name__)


class BrowserServiceRuntimeOpsMixin:
    async def _runtime_navigate(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        url: str,
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.navigate(url=url, timeout_ms=timeout_ms, target_id=target_id),
        )

    async def _runtime_history(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        operation: str,
    ) -> Dict[str, Any]:
        method = operation.lower()
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: getattr(runtime, method)(target_id=target_id, timeout_ms=timeout_ms),
        )

    async def _runtime_snapshot(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        limit: int,
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.snapshot(
                target_id=target_id,
                timeout_ms=timeout_ms,
                limit=limit,
            ),
        )

    async def _runtime_press(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        key: str,
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.press(
                key=key,
                target_id=target_id,
                timeout_ms=timeout_ms,
            ),
        )

    async def _runtime_hover(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.hover(
                target_id=target_id,
                timeout_ms=timeout_ms,
                selector=selector,
                ref=ref,
            ),
        )

    async def _runtime_drag(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        start_selector: Optional[str],
        start_ref: Optional[str],
        end_selector: Optional[str],
        end_ref: Optional[str],
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.drag(
                target_id=target_id,
                timeout_ms=timeout_ms,
                start_selector=start_selector,
                start_ref=start_ref,
                end_selector=end_selector,
                end_ref=end_ref,
            ),
        )

    async def _runtime_scroll(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
        delta_x: int,
        delta_y: int,
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.scroll(
                target_id=target_id,
                timeout_ms=timeout_ms,
                selector=selector,
                ref=ref,
                delta_x=delta_x,
                delta_y=delta_y,
            ),
        )

    async def _runtime_upload(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        paths: list[str],
        selector: Optional[str],
        ref: Optional[str],
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.upload(
                target_id=target_id,
                timeout_ms=timeout_ms,
                paths=paths,
                selector=selector,
                ref=ref,
            ),
        )

    async def _runtime_wait(
        self,
        *,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        selector: Optional[str],
        selector_state: Optional[str],
        text: Optional[str],
        text_gone: Optional[str],
        url_contains: Optional[str],
        time_ms: Optional[int],
        load_state: Optional[str],
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.wait(
                target_id=target_id,
                timeout_ms=timeout_ms,
                selector=selector,
                selector_state=selector_state,
                text=text,
                text_gone=text_gone,
                url_contains=url_contains,
                time_ms=time_ms,
                load_state=load_state,
            ),
        )

    async def _runtime_close_tab(
        self,
        *,
        profile: str,
        headless: bool,
        target_id: str,
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.close_tab(target_id=target_id),
        )

    async def _effective_headless(self, profile: str, requested: bool) -> bool:
        # Hard overrides always win over per-request settings.
        force_headed = _as_bool(os.getenv("AEIVA_BROWSER_FORCE_HEADED"), default=False)
        force_headless = _as_bool(os.getenv("AEIVA_BROWSER_FORCE_HEADLESS"), default=False)
        if force_headed and not force_headless:
            return False
        if force_headless and not force_headed:
            return True
        return bool(requested)

    def _evaluate_policy_error(self, profile: str) -> Optional[Dict[str, Any]]:
        if self._security.allow_evaluate:
            return None
        logger.warning(
            "Blocked browser evaluate operation by policy profile=%s",
            profile,
        )
        return self._err(
            "browser evaluate is disabled by policy. Set "
            "AEIVA_BROWSER_ALLOW_EVALUATE=1 to enable.",
            code="evaluate_disabled",
        )

    async def _run_evaluate_action(
        self,
        *,
        profile: str,
        headless: bool,
        script: str,
        target_id: Optional[str],
        selector: Optional[str],
        ref: Optional[str],
    ) -> Dict[str, Any]:
        return await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.evaluate(
                script=script,
                target_id=target_id,
                selector=selector,
                ref=ref,
            ),
        )

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
        allowed, reason = self._security.validate_request_url(url)
        if not allowed:
            logger.warning("Blocked browser request by policy url=%s reason=%s", url, reason)
            return self._err(reason or "request blocked by policy", code="request_blocked")

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
        return await self._search_engine.run_search(
            query=query,
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
        )
