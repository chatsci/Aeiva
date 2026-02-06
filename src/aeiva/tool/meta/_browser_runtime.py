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
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Protocol


MAX_EVENT_HISTORY = 200
DEFAULT_TIMEOUT_MS = 30_000


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_title(value: Any) -> str:
    try:
        return str(value) if value is not None else ""
    except Exception:
        return ""


def _read_attr(obj: Any, name: str, default: Any = "") -> Any:
    value = getattr(obj, name, default)
    if callable(value):
        try:
            return value()
        except Exception:
            return default
    return value


def _normalize_timeout(timeout_ms: Optional[int], default: int = DEFAULT_TIMEOUT_MS) -> int:
    if timeout_ms is None:
        return default
    try:
        parsed = int(timeout_ms)
    except Exception:
        return default
    return max(1, parsed)


def _is_asyncio_loop_instance(loop: Any) -> bool:
    module = type(loop).__module__
    return module.startswith("asyncio.")


def _has_usable_child_watcher(policy: Any) -> bool:
    getter = getattr(policy, "get_child_watcher", None)
    if not callable(getter):
        return False
    try:
        return getter() is not None
    except Exception:
        return False


def _repair_subprocess_policy_for_loop(loop: Any) -> bool:
    """
    Ensure asyncio subprocess support for a pre-existing stdlib asyncio loop.

    Some web stacks set a custom event-loop policy (e.g. uvloop) after the main
    loop is already created. On Python 3.12 this can break `create_subprocess_exec`
    for that existing loop because policy child watcher APIs may be unavailable.
    """
    if os.name != "posix":
        return False
    if not _is_asyncio_loop_instance(loop):
        return False

    policy = asyncio.get_event_loop_policy()
    if _has_usable_child_watcher(policy):
        return False

    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    repaired_policy = asyncio.get_event_loop_policy()

    getter = getattr(repaired_policy, "get_child_watcher", None)
    setter = getattr(repaired_policy, "set_child_watcher", None)
    watcher = None
    if callable(getter):
        try:
            watcher = getter()
        except Exception:
            watcher = None
    if watcher is None and callable(setter):
        try:
            watcher = asyncio.ThreadedChildWatcher()
            setter(watcher)
        except Exception:
            watcher = None

    if watcher is not None:
        attach_loop = getattr(watcher, "attach_loop", None)
        if callable(attach_loop):
            try:
                attach_loop(loop)
            except Exception:
                pass
    return True


@dataclass
class TabEvents:
    console: Deque[Dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=MAX_EVENT_HISTORY)
    )
    errors: Deque[Dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=MAX_EVENT_HISTORY)
    )
    network: Deque[Dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=MAX_EVENT_HISTORY)
    )


@dataclass
class TabState:
    target_id: str
    page: Any
    refs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    events: TabEvents = field(default_factory=TabEvents)


class BrowserRuntime(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def status(self) -> Dict[str, Any]: ...

    async def list_tabs(self) -> List[Dict[str, Any]]: ...

    async def open_tab(self, url: str, timeout_ms: int) -> Dict[str, Any]: ...

    async def focus_tab(self, target_id: str) -> Dict[str, Any]: ...

    async def close_tab(self, target_id: str) -> Dict[str, Any]: ...

    async def back(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]: ...

    async def forward(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]: ...

    async def reload(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]: ...

    async def navigate(
        self,
        url: str,
        timeout_ms: int,
        target_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def click(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
        double_click: bool = False,
        button: str = "left",
    ) -> Dict[str, Any]: ...

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
    ) -> Dict[str, Any]: ...

    async def press(
        self,
        *,
        key: str,
        target_id: Optional[str],
        timeout_ms: int,
    ) -> Dict[str, Any]: ...

    async def hover(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def select(
        self,
        *,
        values: List[str],
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def drag(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        start_selector: Optional[str] = None,
        start_ref: Optional[str] = None,
        end_selector: Optional[str] = None,
        end_ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def scroll(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
        delta_x: int = 0,
        delta_y: int = 800,
    ) -> Dict[str, Any]: ...

    async def upload(
        self,
        *,
        paths: List[str],
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def wait(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        text_gone: Optional[str] = None,
        url_contains: Optional[str] = None,
        time_ms: Optional[int] = None,
        load_state: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def evaluate(
        self,
        *,
        script: str,
        target_id: Optional[str],
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def screenshot(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        full_page: bool,
        image_type: str,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def pdf(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        scale: float = 1.0,
        print_background: bool = True,
    ) -> Dict[str, Any]: ...

    async def get_text(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def get_html(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        selector: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def snapshot(
        self,
        *,
        target_id: Optional[str],
        timeout_ms: int,
        limit: int,
    ) -> Dict[str, Any]: ...

    async def get_console(
        self,
        *,
        target_id: Optional[str],
        limit: int,
    ) -> Dict[str, Any]: ...

    async def get_errors(
        self,
        *,
        target_id: Optional[str],
        limit: int,
    ) -> Dict[str, Any]: ...

    async def get_network(
        self,
        *,
        target_id: Optional[str],
        limit: int,
    ) -> Dict[str, Any]: ...


class PlaywrightRuntime(BrowserRuntime):
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
        primary_selector, fallback_selector = self._resolve_selector(
            target_id=resolved_target, selector=selector, ref=ref
        )
        locator = await self._wait_for_locator(
            page,
            primary_selector,
            timeout_ms,
            fallback_selector=fallback_selector,
        )
        if slowly:
            await locator.click(timeout=timeout_ms)
            await page.keyboard.type(text or "", delay=60)
        else:
            await locator.fill(text or "", timeout=timeout_ms)
        if submit:
            await page.keyboard.press("Enter", timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

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
        primary_selector, fallback_selector = self._resolve_selector(
            target_id=resolved_target, selector=selector, ref=ref
        )
        locator = await self._wait_for_locator(
            page,
            primary_selector,
            timeout_ms,
            fallback_selector=fallback_selector,
        )
        await locator.select_option(values=values, timeout=timeout_ms)
        return await self._tab_payload(resolved_target)

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
            )
            await locator.scroll_into_view_if_needed(timeout=timeout_ms)
            await locator.hover(timeout=timeout_ms)
        await page.mouse.wheel(int(delta_x), int(delta_y))
        return await self._tab_payload(resolved_target)

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
        resolved_paths = [os.path.expanduser(str(path)) for path in paths]
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
            await page.wait_for_selector(selector, timeout=timeout_ms)
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
        raw_nodes = await page.evaluate(_SNAPSHOT_JS, {"limit": max_items})
        if not isinstance(raw_nodes, list):
            raw_nodes = []

        ref_map: Dict[str, Dict[str, Any]] = {}
        nodes: List[Dict[str, Any]] = []
        lines: List[str] = []

        for idx, node in enumerate(raw_nodes, start=1):
            if not isinstance(node, dict):
                continue
            ref = _safe_title(node.get("ref")).strip() or f"e{idx}"
            selector = _safe_title(node.get("selector")).strip()
            fallback_selector = _safe_title(node.get("fallback_selector")).strip()
            if not selector and not fallback_selector:
                continue

            role = _safe_title(node.get("role")).strip() or _safe_title(node.get("tag")).strip()
            name = _safe_title(node.get("name")).strip()
            text_value = _safe_title(node.get("text")).strip()

            ref_map[ref] = {
                "selector": selector or fallback_selector,
                "fallback_selector": fallback_selector or None,
                "role": role,
                "name": name,
                "text": text_value,
            }

            nodes.append(
                {
                    "ref": ref,
                    "role": role,
                    "name": name,
                    "text": text_value,
                    "selector": selector or fallback_selector,
                    "fallback_selector": fallback_selector or None,
                }
            )

            line_label = name or text_value or selector or fallback_selector
            lines.append(f"{ref} [{role or 'node'}] {line_label}".strip())

        tab = self._tab_states.get(resolved_target)
        if tab is not None:
            tab.refs = ref_map

        return {
            "target_id": resolved_target,
            "url": _safe_title(getattr(page, "url", "")),
            "nodes": nodes,
            "snapshot": "\n".join(lines),
        }

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

    async def _launch_browser_with_fallback(self, playwright: Any) -> tuple[Any, str]:
        browser_type = playwright.chromium
        common_args = ["--disable-dev-shm-usage"]
        requested_headless = bool(self.headless)

        env_executable = os.getenv("AEIVA_BROWSER_EXECUTABLE_PATH", "").strip() or None
        env_channels_raw = os.getenv("AEIVA_BROWSER_CHANNELS", "").strip()
        env_channels = [
            item.strip()
            for item in env_channels_raw.split(",")
            if item.strip()
        ]
        preferred_channels = env_channels or ["chrome", "msedge"]

        def candidate(
            label: str,
            *,
            headless: bool,
            channel: Optional[str] = None,
            executable_path: Optional[str] = None,
        ) -> dict[str, Any]:
            launch_kwargs: Dict[str, Any] = {
                "headless": headless,
                "args": list(common_args),
                "chromium_sandbox": False,
            }
            if channel:
                launch_kwargs["channel"] = channel
            if executable_path:
                launch_kwargs["executable_path"] = executable_path
            return {"label": label, "kwargs": launch_kwargs}

        candidates: List[Dict[str, Any]] = []
        candidates.append(candidate("chromium-default", headless=requested_headless))
        for channel in preferred_channels:
            candidates.append(
                candidate(
                    f"chromium-channel:{channel}",
                    headless=requested_headless,
                    channel=channel,
                )
            )
        if env_executable:
            candidates.append(
                candidate(
                    "chromium-executable-env",
                    headless=requested_headless,
                    executable_path=env_executable,
                )
            )

        if requested_headless:
            candidates.append(candidate("chromium-default-headed-fallback", headless=False))
            for channel in preferred_channels:
                candidates.append(
                    candidate(
                        f"chromium-channel:{channel}-headed-fallback",
                        headless=False,
                        channel=channel,
                    )
                )

        failures: List[str] = []
        seen_signatures: set[str] = set()

        for entry in candidates:
            kwargs = entry["kwargs"]
            signature = repr(sorted(kwargs.items()))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            label = entry["label"]
            try:
                browser = await browser_type.launch(**kwargs)
                return browser, label
            except Exception as exc:
                message = self._compact_exception_message(exc)
                failures.append(f"{label}: {message}")

        guidance = [
            "Failed to launch browser automation.",
            "Set `AEIVA_BROWSER_CHANNELS=chrome` or `AEIVA_BROWSER_EXECUTABLE_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` and retry.",
        ]
        if failures:
            guidance.append("Attempts: " + " | ".join(failures[:5]))
        raise RuntimeError(" ".join(guidance))

    @staticmethod
    def _compact_exception_message(exc: Exception) -> str:
        text = str(exc).strip()
        if not text:
            return exc.__class__.__name__
        lowered = text.lower()
        if "mach_port_rendezvous" in lowered:
            return "macOS launch permission error (mach_port_rendezvous)"
        if "no such file or directory" in lowered:
            return "executable not found"
        if "failed to launch" in lowered:
            return "failed to launch"
        if len(text) > 220:
            return text[:220] + "..."
        return text

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
        try:
            title = await page.title()
        except Exception:
            title = ""
        return {
            "target_id": target_id,
            "url": _safe_title(getattr(page, "url", "")),
            "title": _safe_title(title),
        }

    async def _goto(self, page: Any, url: str, timeout_ms: int) -> None:
        normalized_timeout = _normalize_timeout(timeout_ms)
        last_error: Optional[Exception] = None
        for _ in range(2):
            try:
                await page.goto(
                    url,
                    timeout=normalized_timeout,
                    wait_until="domcontentloaded",
                )
                return
            except Exception as exc:
                last_error = exc
                await page.wait_for_timeout(120)
        if last_error is not None:
            raise last_error

    def _resolve_selector(
        self,
        *,
        target_id: str,
        selector: Optional[str],
        ref: Optional[str],
    ) -> tuple[str, Optional[str]]:
        clean_ref = (ref or "").strip()
        clean_selector = (selector or "").strip()

        if clean_ref:
            tab = self._tab_states.get(target_id)
            if tab:
                entry = tab.refs.get(clean_ref)
                if isinstance(entry, str) and entry.strip():
                    return entry.strip(), None
                if isinstance(entry, dict):
                    primary = _safe_title(entry.get("selector")).strip()
                    fallback = _safe_title(entry.get("fallback_selector")).strip()
                    if primary:
                        return primary, (fallback or None)
                    if fallback:
                        return fallback, None
            raise ValueError(
                f"Unknown ref: {clean_ref}. Call snapshot first and use returned refs."
            )

        if clean_selector:
            return clean_selector, None

        raise ValueError("selector or ref is required")

    async def _wait_for_locator(
        self,
        page: Any,
        selector: str,
        timeout_ms: int,
        *,
        fallback_selector: Optional[str] = None,
    ) -> Any:
        timeout_value = _normalize_timeout(timeout_ms)
        selectors = [selector]
        if fallback_selector and fallback_selector != selector:
            selectors.append(fallback_selector)

        last_error: Optional[Exception] = None
        for candidate in selectors:
            locator = page.locator(candidate).first
            try:
                await locator.wait_for(state="visible", timeout=timeout_value)
                return locator
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise ValueError("Unable to resolve locator")


@dataclass
class BrowserSession:
    profile: str
    headless: bool
    runtime: BrowserRuntime
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


class BrowserSessionManager:
    """
    Profile-scoped browser runtime manager.

    Each profile has one persistent runtime guarded by a per-profile lock.
    """

    def __init__(
        self,
        runtime_factory: Optional[Callable[[str, bool], BrowserRuntime]] = None,
    ) -> None:
        self._runtime_factory = runtime_factory or (
            lambda profile, headless: PlaywrightRuntime(profile=profile, headless=headless)
        )
        self._sessions: Dict[str, BrowserSession] = {}
        self._manager_lock = asyncio.Lock()

    async def get_session(self, profile: str) -> Optional[BrowserSession]:
        async with self._manager_lock:
            return self._sessions.get(profile)

    async def ensure_session(self, profile: str, headless: bool) -> BrowserSession:
        clean_profile = profile.strip() or "default"
        session_to_stop: Optional[BrowserSession] = None
        async with self._manager_lock:
            current = self._sessions.get(clean_profile)
            if current and current.headless == bool(headless):
                return current

            if current is not None:
                self._sessions.pop(clean_profile, None)
                session_to_stop = current

        if session_to_stop is not None:
            async with session_to_stop.lock:
                await session_to_stop.runtime.stop()

        runtime = self._runtime_factory(clean_profile, bool(headless))
        session = BrowserSession(
            profile=clean_profile,
            headless=bool(headless),
            runtime=runtime,
        )
        try:
            await runtime.start()
        except Exception:
            # Ensure partially initialized runtimes do not leak processes/resources.
            try:
                await runtime.stop()
            except Exception:
                pass
            raise

        async with self._manager_lock:
            existing = self._sessions.get(clean_profile)
            if existing is not None:
                async with existing.lock:
                    await existing.runtime.stop()
            self._sessions[clean_profile] = session
        return session

    async def run_with_session(
        self,
        *,
        profile: str,
        headless: bool,
        create: bool,
        fn: Callable[[BrowserRuntime], Any],
    ) -> Any:
        session: Optional[BrowserSession]
        if create:
            session = await self.ensure_session(profile, headless)
        else:
            session = await self.get_session(profile)
            if session is None:
                raise ValueError(f"Browser profile not running: {profile}")

        async with session.lock:
            session.last_used_at = time.time()
            return await fn(session.runtime)

    async def stop_session(self, profile: str) -> bool:
        clean_profile = profile.strip() or "default"
        async with self._manager_lock:
            session = self._sessions.pop(clean_profile, None)
        if session is None:
            return False
        async with session.lock:
            await session.runtime.stop()
        return True

    async def stop_all(self) -> None:
        async with self._manager_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            async with session.lock:
                await session.runtime.stop()

    async def list_profiles(self) -> List[Dict[str, Any]]:
        async with self._manager_lock:
            items = list(self._sessions.values())

        profiles: List[Dict[str, Any]] = []
        for session in items:
            runtime_status = await session.runtime.status()
            profiles.append(
                {
                    "profile": session.profile,
                    "headless": session.headless,
                    "created_at": session.created_at,
                    "last_used_at": session.last_used_at,
                    "status": runtime_status,
                }
            )
        return profiles


_SNAPSHOT_JS = """
({ limit }) => {
  const maxItems = Math.max(1, Math.min(Number(limit || 80), 200));
  const refAttr = "data-aeiva-ref";
  if (!Number.isInteger(window.__aeivaRefCounter) || window.__aeivaRefCounter < 1) {
    window.__aeivaRefCounter = 1;
  }

  const candidates = Array.from(
    document.querySelectorAll(
      "a,button,input,textarea,select,summary,[role],[onclick],[tabindex]"
    )
  );

  const esc = (value) => {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(String(value));
    }
    return String(value).replace(/([ #;?%&,.+*~':!^$[\\]()=>|\\/])/g, "\\\\$1");
  };

  const visible = (el) => {
    if (!(el instanceof HTMLElement)) return false;
    const style = window.getComputedStyle(el);
    if (!style || style.display === "none" || style.visibility === "hidden") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const roleOf = (el) => {
    const explicitRole = el.getAttribute("role");
    if (explicitRole) return explicitRole;
    return el.tagName.toLowerCase();
  };

  const textOf = (el) => {
    const value =
      el.getAttribute("aria-label") ||
      el.getAttribute("title") ||
      ("value" in el ? el.value : "") ||
      el.textContent ||
      "";
    return String(value).replace(/\\s+/g, " ").trim().slice(0, 160);
  };

  const selectorOf = (el) => {
    if (el.id) return `#${esc(el.id)}`;

    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === Node.ELEMENT_NODE && parts.length < 6) {
      let part = cur.tagName.toLowerCase();

      const classes = Array.from(cur.classList || []).filter(Boolean);
      if (classes.length > 0) {
        part += `.${esc(classes[0])}`;
      }

      if (cur.parentElement) {
        const sameTag = Array.from(cur.parentElement.children).filter(
          (node) => node.tagName === cur.tagName
        );
        if (sameTag.length > 1) {
          part += `:nth-of-type(${sameTag.indexOf(cur) + 1})`;
        }
      }

      parts.unshift(part);
      cur = cur.parentElement;
      if (!cur || cur.tagName.toLowerCase() === "html") break;
    }
    return parts.join(" > ");
  };

  const ensureRef = (el) => {
    const existing = (el.getAttribute(refAttr) || "").trim();
    if (existing) return existing;

    let value = "";
    for (let i = 0; i < 20000; i++) {
      const candidate = `e${window.__aeivaRefCounter++}`;
      const owner = document.querySelector(`[${refAttr}="${candidate}"]`);
      if (!owner || owner === el) {
        value = candidate;
        break;
      }
    }
    if (!value) {
      value = `e${Date.now()}`;
    }
    el.setAttribute(refAttr, value);
    return value;
  };

  const seen = new Set();
  const out = [];
  for (const el of candidates) {
    if (!visible(el)) continue;
    const fallbackSelector = selectorOf(el);
    const ref = ensureRef(el);
    const stableSelector = `[${refAttr}="${ref}"]`;

    if ((!stableSelector && !fallbackSelector) || seen.has(ref)) continue;
    seen.add(ref);
    out.push({
      ref,
      tag: el.tagName.toLowerCase(),
      role: roleOf(el),
      name: textOf(el),
      text: String(el.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 160),
      selector: stableSelector,
      fallback_selector: fallbackSelector
    });
    if (out.length >= maxItems) break;
  }
  return out;
}
"""
