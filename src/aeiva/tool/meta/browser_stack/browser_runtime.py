"""
Internal Browser V2 runtime primitives.

This module provides:
- `BrowserRuntime` protocol for backend abstraction.
- `PlaywrightRuntime` for local persistent browser automation.
- `BrowserSessionManager` for profile-scoped lifecycle and concurrency control.

It is intentionally not auto-discovered as a tool module.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

from .runtime_content import RuntimeContentMixin
from .runtime_interaction import RuntimeInteractionMixin
from .runtime_launch import RuntimeLaunchMixin
from .runtime_state import RuntimeStateMixin
from .runtime_common import (
    DEFAULT_SELECT_SETTLE_MS,
    DEFAULT_SLOW_TYPE_DELAY_MS,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_TYPE_DELAY_MS,
    BrowserRuntime,
    _distributed_attempt_timeout,
    _extract_numeric_token,
    _normalize_text_value,
    _normalize_timeout,
    _parse_int_env,
    _repair_subprocess_policy_for_loop,
    _safe_title,
)
from .session_manager import BrowserSessionManager
from .security import BrowserSecurityPolicy
from .runtime_scroll_script import ACTIVE_CONTAINER_SCROLL_JS, ELEMENT_SCROLL_JS

logger = logging.getLogger(__name__)


class PlaywrightRuntime(
    RuntimeContentMixin,
    RuntimeStateMixin,
    RuntimeLaunchMixin,
    RuntimeInteractionMixin,
    BrowserRuntime,
):
    """Persistent local Playwright runtime for one profile."""

    def __init__(self, profile: str, headless: bool = True):
        self.profile = profile
        self.headless = bool(headless)

        self._started = False
        self._started_at: Optional[float] = None
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None

        self._next_tab_id = 1
        self._tab_states: Dict[str, TabState] = {}
        self._page_to_tab: Dict[int, str] = {}
        self._last_target_id: Optional[str] = None
        self._launch_strategy: Optional[str] = None
        self._launch_user_data_dir: Optional[str] = None
        self._security = BrowserSecurityPolicy.from_env()

    async def start(self) -> None:
        if self._started:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is not installed. Install extras: pip install -e '.[tools]'"
            ) from exc

        loop = asyncio.get_running_loop()
        _repair_subprocess_policy_for_loop(loop)
        for attempt in range(2):
            try:
                self._playwright = await async_playwright().start()
                self._browser, self._launch_strategy = await self._launch_browser_with_fallback(
                    self._playwright
                )
                self._context = await self._browser.new_context()
                self._context.on("page", self._on_page_created)
                self._started = True
                self._started_at = time.time()
                logger.info(
                    "Browser runtime started profile=%s headless=%s launch_strategy=%s",
                    self.profile,
                    self.headless,
                    self._launch_strategy,
                )
                return
            except NotImplementedError as exc:
                await self._cleanup_partial_start()
                if attempt == 0 and _repair_subprocess_policy_for_loop(loop):
                    continue
                raise RuntimeError(
                    "Browser launch failed because asyncio subprocess support is unavailable "
                    "for the current runtime loop. This often happens when event-loop policy "
                    "is changed after loop creation."
                ) from exc
            except Exception:
                await self._cleanup_partial_start()
                raise

    async def _cleanup_partial_start(self) -> None:
        context = self._context
        browser = self._browser
        playwright = self._playwright

        self._started = False
        self._started_at = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._launch_strategy = None
        self._tab_states.clear()
        self._page_to_tab.clear()
        self._last_target_id = None

        try:
            if context is not None:
                await context.close()
        except Exception:
            pass
        try:
            if browser is not None:
                await browser.close()
        except Exception:
            pass
        try:
            if playwright is not None:
                await playwright.stop()
        except Exception:
            pass
        self._cleanup_launch_user_data_dir()

    async def stop(self) -> None:
        if not self._started:
            return

        context = self._context
        browser = self._browser
        playwright = self._playwright

        self._started = False
        self._started_at = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._tab_states.clear()
        self._page_to_tab.clear()
        self._last_target_id = None

        try:
            if context is not None:
                await context.close()
        finally:
            try:
                if browser is not None:
                    await browser.close()
            finally:
                if playwright is not None:
                    await playwright.stop()
        self._cleanup_launch_user_data_dir()
        logger.info("Browser runtime stopped profile=%s", self.profile)

    def _ensure_launch_user_data_dir(self) -> str:
        existing = self._launch_user_data_dir
        if existing:
            return existing
        safe_profile = re.sub(r"[^A-Za-z0-9_.-]+", "-", self.profile).strip("-") or "default"
        created = tempfile.mkdtemp(prefix=f"aeiva-browser-{safe_profile}-")
        self._launch_user_data_dir = created
        return created

    def _cleanup_launch_user_data_dir(self) -> None:
        path = self._launch_user_data_dir
        self._launch_user_data_dir = None
        if not path:
            return
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass

    async def status(self) -> Dict[str, Any]:
        tab_count = len(self._tab_states)
        return {
            "running": self._started,
            "profile": self.profile,
            "headless": self.headless,
            "tab_count": tab_count,
            "last_target_id": self._last_target_id,
            "started_at": self._started_at,
            "launch_strategy": self._launch_strategy,
        }

    async def list_tabs(self) -> List[Dict[str, Any]]:
        await self._ensure_started()
        await self._sync_known_pages()

        tabs: List[Dict[str, Any]] = []
        for target_id, tab in self._tab_states.items():
            page = tab.page
            title = ""
            try:
                title = await page.title()
            except Exception:
                title = ""
            tabs.append(
                {
                    "target_id": target_id,
                    "title": _safe_title(title),
                    "url": _safe_title(getattr(page, "url", "")),
                    "active": target_id == self._last_target_id,
                }
            )
        return tabs

    async def open_tab(self, url: str, timeout_ms: int) -> Dict[str, Any]:
        await self._ensure_started()
        page = await self._context.new_page()
        target_id = self._register_page(page)

        clean_url = (url or "").strip()
        if clean_url:
            await self._goto(page, clean_url, timeout_ms)

        return await self._tab_payload(target_id)

    async def focus_tab(self, target_id: str) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=False)
        await page.bring_to_front()
        self._last_target_id = resolved_target
        return await self._tab_payload(resolved_target)

    async def close_tab(self, target_id: str) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=False)
        await page.close()
        return {
            "closed_target_id": resolved_target,
            "remaining_tabs": len(self._tab_states),
        }

    async def back(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        await page.go_back(timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

    async def forward(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        await page.go_forward(timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

    async def reload(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        await page.reload(timeout=timeout_ms, wait_until="domcontentloaded")
        return await self._tab_payload(resolved_target)

    async def navigate(
        self,
        url: str,
        timeout_ms: int,
        target_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean_url = (url or "").strip()
        if not clean_url:
            raise ValueError("URL required for navigate operation")

        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        await self._goto(page, clean_url, timeout_ms)
        return await self._tab_payload(resolved_target)

    async def click(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
        double_click: bool = False,
        button: str = "left",
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        primary_selector, fallback_selector = self._resolve_selector(
            target_id=resolved_target, selector=selector, ref=ref
        )
        locator = await self._wait_for_locator(
            page,
            primary_selector,
            timeout_ms,
            fallback_selector=fallback_selector,
        )
        if double_click:
            await locator.dblclick(button=button, timeout=timeout_ms)
        else:
            await locator.click(button=button, timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

    async def type_text(
        self,
        *,
        text: str,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
        submit: bool = False,
        slowly: bool = False,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        payload_text = text or ""
        locator: Optional[Any] = None

        if selector or ref:
            primary_selector, fallback_selector = self._resolve_selector(
                target_id=resolved_target, selector=selector, ref=ref
            )
            locator = await self._wait_for_locator(
                page,
                primary_selector,
                timeout_ms,
                fallback_selector=fallback_selector,
                allow_attached_fallback=True,
            )
        elif not await self._focused_element_is_editable(page):
            locator = await self._find_best_editable_locator(page, timeout_ms)
            if locator is None:
                raise ValueError(
                    "selector or ref is required unless an editable element is already focused"
                )

        typed = await self._write_text_with_fallback(
            page=page,
            locator=locator,
            text=payload_text,
            timeout_ms=timeout_ms,
            slowly=slowly,
        )
        typed_ok, typed_locator = typed
        if not typed_ok:
            raise ValueError("Unable to type text into target field")
        if submit:
            await page.keyboard.press("Enter", timeout=timeout_ms)
        payload = await self._tab_payload(resolved_target)
        try:
            payload["field_value"] = await self._read_field_value(
                page=page,
                locator=typed_locator if typed_locator is not None else locator,
            )
        except Exception:
            pass
        return payload

    async def _write_text_with_fallback(
        self,
        *,
        page: Any,
        locator: Optional[Any],
        text: str,
        timeout_ms: int,
        slowly: bool,
    ) -> tuple[bool, Optional[Any]]:
        if locator is None:
            await self._type_via_keyboard(
                page,
                locator,
                text,
                timeout_ms,
                slowly=slowly,
            )
            return await self._text_matches_active(page, text), None

        if not slowly:
            try:
                await locator.fill(text, timeout=timeout_ms)
                if await self._text_matches_locator(locator, text):
                    return True, locator
            except Exception:
                pass

        await self._type_via_keyboard(
            page,
            locator,
            text,
            timeout_ms,
            slowly=slowly,
        )
        if await self._text_matches_locator(locator, text):
            return True, locator
        if await self._text_matches_active(page, text):
            return True, locator

        if await self._apply_numeric_value_fallback(
            locator=locator,
            text=text,
            timeout_ms=timeout_ms,
        ):
            if await self._text_matches_locator(locator, text):
                return True, locator

        editable = await self._find_editable_within_locator(locator, timeout_ms)
        if editable is None:
            # Do not spill targeted writes into an unrelated global input.
            # If this scoped target has no editable descendant, fail fast so
            # the caller can recover with a better ref/selector.
            return False, locator
        await self._type_via_keyboard(
            page,
            editable,
            text,
            timeout_ms,
            slowly=slowly,
        )
        if await self._text_matches_locator(editable, text):
            return True, editable
        return await self._text_matches_active(page, text), editable

    async def press(
        self,
        *,
        key: str,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        if not key:
            raise ValueError("Key is required for press operation")
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        await page.keyboard.press(key, timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

    async def hover(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        primary_selector, fallback_selector = self._resolve_selector(
            target_id=resolved_target, selector=selector, ref=ref
        )
        locator = await self._wait_for_locator(
            page,
            primary_selector,
            timeout_ms,
            fallback_selector=fallback_selector,
        )
        await locator.hover(timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

    async def select(
        self,
        *,
        values: List[str],
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not values:
            raise ValueError("values are required for select operation")
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        locator: Optional[Any] = None
        if selector or ref:
            primary_selector, fallback_selector = self._resolve_selector(
                target_id=resolved_target, selector=selector, ref=ref
            )
            locator = await self._wait_for_locator(
                page,
                primary_selector,
                timeout_ms,
                fallback_selector=fallback_selector,
                allow_attached_fallback=True,
            )
            try:
                await locator.select_option(value=values, timeout=timeout_ms)
            except Exception:
                await self._select_custom_values(
                    page=page,
                    control_locator=locator,
                    values=values,
                    timeout_ms=timeout_ms,
                )
        else:
            await self._select_values_from_open_dropdown(
                page=page,
                values=values,
                timeout_ms=timeout_ms,
            )
        payload = await self._tab_payload(resolved_target)
        try:
            payload["selected_values"] = await self._read_selected_values(
                page=page,
                locator=locator,
            )
        except Exception:
            pass
        return payload

    async def drag(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        start_selector: Optional[str] = None,
        start_ref: Optional[str] = None,
        end_selector: Optional[str] = None,
        end_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        start_primary, start_fallback = self._resolve_selector(
            target_id=resolved_target,
            selector=start_selector,
            ref=start_ref,
        )
        end_primary, end_fallback = self._resolve_selector(
            target_id=resolved_target,
            selector=end_selector,
            ref=end_ref,
        )
        start_locator = await self._wait_for_locator(
            page,
            start_primary,
            timeout_ms,
            fallback_selector=start_fallback,
        )
        end_locator = await self._wait_for_locator(
            page,
            end_primary,
            timeout_ms,
            fallback_selector=end_fallback,
        )
        await start_locator.drag_to(end_locator, timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

    async def scroll(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
        delta_x: int = 0,
        delta_y: int = 800,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        viewport_before = await self._read_viewport_scroll(page)
        element_scrolled = False
        element_scroll: Optional[Dict[str, Any]] = None
        active_container_scroll: Optional[Dict[str, Any]] = None

        if selector or ref:
            primary, fallback = self._resolve_selector(
                target_id=resolved_target,
                selector=selector,
                ref=ref,
            )
            locator = await self._wait_for_locator(
                page,
                primary,
                timeout_ms,
                fallback_selector=fallback,
                allow_attached_fallback=True,
            )
            try:
                element_scroll = await locator.evaluate(
                    ELEMENT_SCROLL_JS,
                    {"x": int(delta_x), "y": int(delta_y)},
                )
                if isinstance(element_scroll, dict) and bool(element_scroll.get("scrolled")):
                    element_scrolled = True
            except Exception:
                element_scrolled = False

        if not element_scrolled:
            # When interacting with dialogs (date pickers, dropdown panels),
            # scrolling the nearest active container is more stable than
            # moving the whole page viewport.
            active_container_scroll = await self._scroll_active_container(
                page=page,
                delta_x=int(delta_x),
                delta_y=int(delta_y),
            )
            if isinstance(active_container_scroll, dict) and bool(active_container_scroll.get("scrolled")):
                element_scrolled = True
            else:
                await page.mouse.wheel(int(delta_x), int(delta_y))

        viewport_after = await self._read_viewport_scroll(page)
        viewport_moved = (
            int(viewport_before.get("x", 0)) != int(viewport_after.get("x", 0))
            or int(viewport_before.get("y", 0)) != int(viewport_after.get("y", 0))
        )
        scroll_effective = bool(element_scrolled or viewport_moved)
        payload = await self._tab_payload(resolved_target)
        payload.update(
            {
                "scrolled_container": bool(element_scrolled),
                "scroll_effective": scroll_effective,
                "container_scroll": element_scroll if isinstance(element_scroll, dict) else None,
                "active_container_scroll": (
                    active_container_scroll if isinstance(active_container_scroll, dict) else None
                ),
                "viewport_scroll_before": viewport_before,
                "viewport_scroll_after": viewport_after,
            }
        )
        return payload

    async def _scroll_active_container(
        self,
        *,
        page: Any,
        delta_x: int,
        delta_y: int,
    ) -> Optional[Dict[str, Any]]:
        try:
            result = await page.evaluate(
                ACTIVE_CONTAINER_SCROLL_JS,
                {"x": int(delta_x), "y": int(delta_y)},
            )
        except Exception:
            return None
        if not isinstance(result, dict):
            return None
        return result

    async def upload(
        self,
        *,
        paths: List[str],
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not paths:
            raise ValueError("paths are required for upload operation")
        resolved_paths = self._security.resolve_upload_paths(paths)
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        primary, fallback = self._resolve_selector(
            target_id=resolved_target,
            selector=selector,
            ref=ref,
        )
        locator = await self._wait_for_locator(
            page,
            primary,
            timeout_ms,
            fallback_selector=fallback,
        )
        await locator.set_input_files(resolved_paths, timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

    async def wait(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        selector_state: Optional[str] = None,
        text: Optional[str] = None,
        text_gone: Optional[str] = None,
        url_contains: Optional[str] = None,
        time_ms: Optional[int] = None,
        load_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)

        waited = False
        if time_ms is not None:
            await page.wait_for_timeout(max(0, int(time_ms)))
            waited = True
        if selector:
            state = self._normalize_selector_state(selector_state)
            await page.wait_for_selector(selector, timeout=timeout_ms, state=state)
            waited = True
        if text:
            await page.get_by_text(text).first.wait_for(timeout=timeout_ms)
            waited = True
        if text_gone:
            await page.get_by_text(text_gone).first.wait_for(
                state="hidden",
                timeout=timeout_ms,
            )
            waited = True
        if url_contains:
            await page.wait_for_url(f"**{url_contains}**", timeout=timeout_ms)
            waited = True
        if load_state:
            await page.wait_for_load_state(load_state, timeout=timeout_ms)
            waited = True

        if not waited:
            raise ValueError(
                "wait requires one of: time_ms, selector, text, text_gone, url_contains, load_state"
            )

        return await self._tab_payload(resolved_target)

    async def evaluate(
        self,
        *,
        script: str,
        target_id: Optional[str],
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not script:
            raise ValueError("script is required for evaluate operation")

        page, resolved_target = await self._resolve_page(target_id=target_id, create=True)
        result: Any
        if selector or ref:
            primary_selector, fallback_selector = self._resolve_selector(
                target_id=resolved_target, selector=selector, ref=ref
            )
            locator = await self._wait_for_locator(
                page,
                primary_selector,
                DEFAULT_TIMEOUT_MS,
                fallback_selector=fallback_selector,
            )
            result = await locator.evaluate(script)
        else:
            result = await page.evaluate(script)

        payload = await self._tab_payload(resolved_target)
        payload["result"] = result
        return payload
