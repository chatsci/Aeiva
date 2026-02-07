"""Search orchestration engine for BrowserService."""

from __future__ import annotations

from urllib.parse import quote_plus
from typing import Any, Dict, Optional

from .element_matching import _match_snapshot_nodes
from .service_utils import (
    _build_flight_comparison_links,
    _build_search_fallback_results,
    _looks_like_flight_query,
    _looks_like_google_sorry,
)


class SearchEngine:
    def __init__(self, *, service: Any) -> None:
        self._service = service

    async def run_search(
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
            return self._service._err("Query required for search operation")
        comparison_links = _build_flight_comparison_links(clean) if _looks_like_flight_query(clean) else []

        if target_id:
            return await self._run_in_page_search(
                clean=clean,
                profile=profile,
                headless=headless,
                timeout_ms=timeout_ms,
                target_id=target_id,
            )

        search_url = f"https://www.google.com/search?q={quote_plus(clean)}"
        browser_result = await self._run_browser_navigation_search(
            clean=clean,
            profile=profile,
            headless=headless,
            timeout_ms=timeout_ms,
            target_id=target_id,
            comparison_links=comparison_links,
        )
        if browser_result is not None:
            return browser_result
        return await self._run_fallback_search(
            clean=clean,
            search_url=search_url,
            comparison_links=comparison_links,
        )

    async def _run_in_page_search(
        self,
        *,
        clean: str,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: str,
    ) -> Dict[str, Any]:
        try:
            snapshot_payload = await self._service._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.snapshot(
                    target_id=target_id,
                    timeout_ms=timeout_ms,
                    limit=180,
                ),
            )
        except Exception as exc:
            if "unknown target_id" not in str(exc).lower():
                return self._service._err(
                    f"In-page search failed: {exc}",
                    code="runtime_error",
                    details={"target_id": target_id, "mode": "in_page"},
                )
            try:
                snapshot_payload = await self._service._sessions.run_with_session(
                    profile=profile,
                    headless=headless,
                    create=True,
                    fn=lambda runtime: runtime.snapshot(
                        target_id=None,
                        timeout_ms=timeout_ms,
                        limit=180,
                    ),
                )
            except Exception as nested_exc:
                return self._service._err(
                    f"In-page search failed: {nested_exc}",
                    code="runtime_error",
                    details={"target_id": target_id, "mode": "in_page"},
                )

        nodes = snapshot_payload.get("nodes")
        if not isinstance(nodes, list):
            nodes = []
        matches = _match_snapshot_nodes(nodes, clean)
        return self._service._ok(
            query=clean,
            mode="in_page",
            target_id=snapshot_payload.get("target_id") or target_id,
            url=snapshot_payload.get("url"),
            match_count=len(matches),
            total_nodes=len(nodes),
            matches=matches,
        )

    async def _run_browser_navigation_search(
        self,
        *,
        clean: str,
        profile: str,
        headless: bool,
        timeout_ms: int,
        target_id: Optional[str],
        comparison_links: list[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        search_url = f"https://www.google.com/search?q={quote_plus(clean)}"
        try:
            payload = await self._service._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.navigate(
                    url=search_url,
                    timeout_ms=timeout_ms,
                    target_id=target_id,
                ),
            )
        except Exception:
            return None

        if _looks_like_google_sorry(payload):
            bing_url = f"https://www.bing.com/search?q={quote_plus(clean)}"
            payload = await self._service._sessions.run_with_session(
                profile=profile,
                headless=headless,
                create=True,
                fn=lambda runtime: runtime.navigate(
                    url=bing_url,
                    timeout_ms=timeout_ms,
                    target_id=payload.get("target_id") or target_id,
                ),
            )
            return self._service._ok(
                query=clean,
                engine="bing",
                note="Google presented anti-bot verification; switched to Bing.",
                comparison_links=comparison_links if comparison_links else None,
                **payload,
            )
        return self._service._ok(
            query=clean,
            engine="google",
            comparison_links=comparison_links if comparison_links else None,
            **payload,
        )

    async def _run_fallback_search(
        self,
        *,
        clean: str,
        search_url: str,
        comparison_links: list[Dict[str, str]],
    ) -> Dict[str, Any]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return self._service._ok(
                query=clean,
                engine="fallback_links",
                results=_build_search_fallback_results(clean),
                search_url=search_url,
                comparison_links=comparison_links if comparison_links else None,
                note=(
                    "Browser navigation and duckduckgo-search are unavailable; "
                    "returning actionable URL results."
                ),
            )

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(clean, max_results=10))
        except Exception as exc:
            return self._service._ok(
                query=clean,
                engine="fallback_links",
                results=_build_search_fallback_results(clean),
                search_url=search_url,
                comparison_links=comparison_links if comparison_links else None,
                note=f"duckduckgo-search failed ({exc}); returning actionable URL results.",
            )
        return self._service._ok(
            query=clean,
            results=results,
            engine="duckduckgo",
            comparison_links=comparison_links if comparison_links else None,
        )
