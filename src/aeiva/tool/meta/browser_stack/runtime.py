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

from .runtime_interaction import RuntimeInteractionMixin
from .runtime_launch import RuntimeLaunchMixin
from .runtime_snapshot_script import _SNAPSHOT_JS
from .runtime_common import (
    DEFAULT_POST_GOTO_SETTLE_MS,
    DEFAULT_SELECT_SETTLE_MS,
    DEFAULT_SLOW_TYPE_DELAY_MS,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_TYPE_DELAY_MS,
    BrowserRuntime,
    TabState,
    _coerce_bool,
    _distributed_attempt_timeout,
    _extract_numeric_token,
    _normalize_text_value,
    _normalize_timeout,
    _now_iso,
    _parse_int_env,
    _read_attr,
    _repair_subprocess_policy_for_loop,
    _safe_title,
)
from .session_manager import BrowserSessionManager
from .security import BrowserSecurityPolicy

logger = logging.getLogger(__name__)


class PlaywrightRuntime(RuntimeLaunchMixin, RuntimeInteractionMixin, BrowserRuntime):
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
                    """(el, delta) => {
                      const dx = Number(delta?.x || 0);
                      const dy = Number(delta?.y || 0);
                      const canScrollX = (el.scrollWidth || 0) > (el.clientWidth || 0);
                      const canScrollY = (el.scrollHeight || 0) > (el.clientHeight || 0);
                      if (!canScrollX && !canScrollY) {
                        return {
                          scrolled: false,
                          left: Number(el.scrollLeft || 0),
                          top: Number(el.scrollTop || 0)
                        };
                      }
                      if (typeof el.scrollBy === "function") {
                        el.scrollBy(dx, dy);
                      } else {
                        el.scrollLeft = Number(el.scrollLeft || 0) + dx;
                        el.scrollTop = Number(el.scrollTop || 0) + dy;
                      }
                      return {
                        scrolled: true,
                        left: Number(el.scrollLeft || 0),
                        top: Number(el.scrollTop || 0)
                      };
                    }""",
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
                """(delta) => {
                  const dx = Number(delta?.x || 0);
                  const dy = Number(delta?.y || 0);

                  const isVisible = (el) => {
                    if (!(el instanceof HTMLElement)) return false;
                    const style = window.getComputedStyle(el);
                    if (!style) return false;
                    if (style.display === "none" || style.visibility === "hidden") return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                  };

                  const isScrollable = (el) => {
                    if (!(el instanceof HTMLElement)) return false;
                    const canX = (el.scrollWidth || 0) > (el.clientWidth || 0) + 1;
                    const canY = (el.scrollHeight || 0) > (el.clientHeight || 0) + 1;
                    return canX || canY;
                  };

                  const buildContainerKey = (el) => {
                    if (!(el instanceof HTMLElement)) return "";
                    const tag = String(el.tagName || "").toLowerCase();
                    const id = String(el.id || "").trim();
                    const classes = String(el.className || "")
                      .trim()
                      .split(/\\s+/)
                      .filter(Boolean)
                      .slice(0, 2)
                      .join(".");
                    const role = String(el.getAttribute("role") || "").trim();
                    const aria = String(el.getAttribute("aria-label") || "").trim().slice(0, 24);
                    return [tag, id, classes, role, aria].filter(Boolean).join("|");
                  };

                  const collectAncestors = (node) => {
                    const out = [];
                    let cur = node;
                    while (cur && cur instanceof HTMLElement && out.length < 16) {
                      out.push(cur);
                      cur = cur.parentElement;
                    }
                    return out;
                  };

                  const candidates = [];
                  const active = document.activeElement;
                  if (active instanceof HTMLElement) {
                    candidates.push(...collectAncestors(active));
                  }

                  const overlays = Array.from(
                    document.querySelectorAll(
                      "[aria-modal='true'], [role='dialog'], [role='listbox'], [role='menu'], [role='region']"
                    )
                  );
                  for (const el of overlays) {
                    if (el instanceof HTMLElement) candidates.push(el);
                  }

                  const seen = new Set();
                  const ordered = [];
                  for (const item of candidates) {
                    if (!(item instanceof HTMLElement)) continue;
                    if (!isVisible(item) || !isScrollable(item)) continue;
                    if (seen.has(item)) continue;
                    seen.add(item);
                    ordered.push(item);
                  }
                  if (!ordered.length) {
                    return { scrolled: false };
                  }

                  const scoreForDirection = (el) => {
                    const top = Number(el.scrollTop || 0);
                    const left = Number(el.scrollLeft || 0);
                    const maxTop = Math.max(0, Number(el.scrollHeight || 0) - Number(el.clientHeight || 0));
                    const maxLeft = Math.max(0, Number(el.scrollWidth || 0) - Number(el.clientWidth || 0));
                    const roomY = dy > 0
                      ? Math.max(0, maxTop - top)
                      : dy < 0
                        ? Math.max(0, top)
                        : Math.max(top, Math.max(0, maxTop - top));
                    const roomX = dx > 0
                      ? Math.max(0, maxLeft - left)
                      : dx < 0
                        ? Math.max(0, left)
                        : Math.max(left, Math.max(0, maxLeft - left));
                    const primaryRoom = Math.abs(dy) >= Math.abs(dx) ? roomY : roomX;
                    const secondaryRoom = Math.abs(dy) >= Math.abs(dx) ? roomX : roomY;
                    const area = Number(el.clientWidth || 0) * Number(el.clientHeight || 0);
                    return {
                      roomX,
                      roomY,
                      score: primaryRoom * 1000 + secondaryRoom * 100 + Math.min(area, 2_000_000) / 2000
                    };
                  };

                  let target = null;
                  let targetMeta = null;
                  for (const candidate of ordered) {
                    const meta = scoreForDirection(candidate);
                    const hasRoom = meta.roomX > 1 || meta.roomY > 1;
                    if (!hasRoom) continue;
                    if (!targetMeta || meta.score > targetMeta.score) {
                      target = candidate;
                      targetMeta = meta;
                    }
                  }
                  if (!(target instanceof HTMLElement)) {
                    target = ordered[0];
                    targetMeta = scoreForDirection(target);
                  }

                  const before = {
                    left: Number(target.scrollLeft || 0),
                    top: Number(target.scrollTop || 0),
                  };
                  if (typeof target.scrollBy === "function") {
                    target.scrollBy(dx, dy);
                  } else {
                    target.scrollLeft = Number(target.scrollLeft || 0) + dx;
                    target.scrollTop = Number(target.scrollTop || 0) + dy;
                  }
                  const after = {
                    left: Number(target.scrollLeft || 0),
                    top: Number(target.scrollTop || 0),
                  };
                  const scrolled = before.left !== after.left || before.top !== after.top;
                  return {
                    scrolled,
                    before,
                    after,
                    role: String(target.getAttribute("role") || ""),
                    aria_label: String(target.getAttribute("aria-label") || ""),
                    container_key: buildContainerKey(target),
                    room_x: Number(targetMeta?.roomX || 0),
                    room_y: Number(targetMeta?.roomY || 0),
                  };
                }""",
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
        except Exception:
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
