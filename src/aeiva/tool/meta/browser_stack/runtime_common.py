"""Shared constants, protocols, and helpers for browser runtime modules."""

from __future__ import annotations

import asyncio
import os
import re
import time
import warnings
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Protocol


MAX_EVENT_HISTORY = 200
DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_POST_GOTO_SETTLE_MS = 650
DEFAULT_TYPE_DELAY_MS = 6
DEFAULT_SLOW_TYPE_DELAY_MS = 35
DEFAULT_SELECT_SETTLE_MS = 120


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_title(value: Any) -> str:
    try:
        return str(value) if value is not None else ""
    except Exception:
        return ""


def _normalize_text_value(value: Any) -> str:
    text = _safe_title(value).replace("\u00A0", " ")
    return " ".join(text.split()).strip().casefold()


def _extract_numeric_token(value: Any) -> Optional[float]:
    text = _safe_title(value).strip()
    if not text:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    token = match.group(0).replace(",", ".")
    try:
        parsed = float(token)
    except Exception:
        return None
    if not (parsed == parsed):  # NaN guard
        return None
    return parsed


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _safe_title(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return bool(value)


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


def _distributed_attempt_timeout(
    timeout_ms: int,
    *,
    probe_count: int,
    minimum: int,
    maximum: int,
) -> int:
    timeout_value = _normalize_timeout(timeout_ms)
    if probe_count <= 0:
        return max(minimum, min(maximum, timeout_value))
    per_probe = timeout_value // max(1, int(probe_count))
    return max(minimum, min(maximum, per_probe))


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    text = raw.strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int_env(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return max(minimum, int(default))
    try:
        parsed = int(raw.strip())
    except Exception:
        return max(minimum, int(default))
    return max(minimum, parsed)


def _is_asyncio_loop_instance(loop: Any) -> bool:
    module = type(loop).__module__
    return module.startswith("asyncio.")


def _has_usable_child_watcher(policy: Any) -> bool:
    getter = getattr(policy, "get_child_watcher", None)
    if not callable(getter):
        return False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
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
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
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
        selector_state: Optional[str] = None,
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
