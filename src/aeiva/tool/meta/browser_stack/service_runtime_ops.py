"""Runtime and network operation mixin for BrowserService."""

from __future__ import annotations

import logging
import os
from urllib.parse import quote_plus
from typing import Any, Dict, Optional

from .logging_utils import _log_browser_event
from .service_utils import (
    _as_bool,
    _build_search_fallback_results,
    _extract_search_query_from_url,
    _looks_like_bot_challenge,
)

logger = logging.getLogger(__name__)
DEFAULT_SEARCH_NAV_FALLBACK_TIMEOUT_MS = 12_000


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
        search_query = _extract_search_query_from_url(url)
        navigate_timeout = (
            min(int(timeout_ms), DEFAULT_SEARCH_NAV_FALLBACK_TIMEOUT_MS)
            if search_query
            else int(timeout_ms)
        )
        payload = await self._sessions.run_with_session(
            profile=profile,
            headless=headless,
            create=True,
            fn=lambda runtime: runtime.navigate(
                url=url,
                timeout_ms=navigate_timeout,
                target_id=target_id,
            ),
        )
        if not search_query or not _looks_like_bot_challenge(payload):
            return payload

        challenge_source_url = str(payload.get("url") or url)
        fallback_target_id = payload.get("target_id") or target_id
        fallback_chain = (
            ("bing", f"https://www.bing.com/search?q={quote_plus(search_query)}"),
            ("duckduckgo", f"https://duckduckgo.com/?q={quote_plus(search_query)}"),
        )
        for engine, fallback_url in fallback_chain:
            try:
                candidate = await self._sessions.run_with_session(
                    profile=profile,
                    headless=headless,
                    create=True,
                    fn=lambda runtime, _url=fallback_url: runtime.navigate(
                        url=_url,
                        timeout_ms=navigate_timeout,
                        target_id=fallback_target_id,
                    ),
                )
            except Exception as exc:
                _log_browser_event(
                    logger,
                    level=logging.DEBUG,
                    event="navigate_fallback_failed",
                    engine=engine,
                    error=str(exc),
                )
                continue

            if _looks_like_bot_challenge(candidate):
                continue

            candidate["challenge_detected"] = True
            candidate["challenge_source_url"] = challenge_source_url
            candidate["engine"] = engine
            candidate["note"] = (
                "Search engine challenge detected; switched to Bing."
                if engine == "bing"
                else "Search engine challenge detected; switched to DuckDuckGo."
            )
            return candidate

        payload["challenge_detected"] = True
        payload["challenge_source_url"] = challenge_source_url
        payload["engine"] = "fallback_links"
        payload["search_url"] = url
        payload["results"] = _build_search_fallback_results(search_query)
        payload["success"] = False
        payload["error"] = "Search engine anti-bot challenge blocked automated navigation."
        payload["error_code"] = "anti_bot_challenge"
        payload["note"] = (
            "Search engine challenge detected and alternate engines were also blocked. "
            "Returning actionable fallback links."
        )
        return payload

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
        _log_browser_event(
            logger,
            level=logging.WARNING,
            event="evaluate_blocked_by_policy",
            profile=profile,
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
            _log_browser_event(
                logger,
                level=logging.WARNING,
                event="request_blocked_by_policy",
                url=url,
                reason=reason,
            )
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
