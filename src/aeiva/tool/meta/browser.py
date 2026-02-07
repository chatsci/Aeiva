"""
Browser Tool: Universal web interaction.

Browser V2 adds persistent profiles/tabs and deterministic snapshot+ref actions,
while preserving the legacy operation-style API.
"""

from typing import Any, Dict, List, Optional

from ..capability import Capability
from ..decorator import tool
from .browser_stack.browser_service import get_browser_service


@tool(
    description=(
        "Perform browser operations: status, start, stop, profiles, tabs, open, focus, close, "
        "navigate, back, forward, reload, click, type, set_number, set_date, fill_fields, workflow, submit, "
        "press, hover, select, choose_option, drag, scroll, upload, wait, evaluate, snapshot, act, confirm, screenshot, pdf, get_text, get_html, console, errors, "
        "network, request, search. This tool supports visible (non-headless) automation by default."
    ),
    capabilities=[Capability.BROWSER, Capability.NETWORK],
)
async def browser(
    operation: str,
    url: Optional[str] = None,
    selector: Optional[str] = None,
    text: Optional[str] = None,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    query: Optional[str] = None,
    timeout: int = 20000,
    headless: bool = False,
    profile: str = "default",
    target_id: Optional[str] = None,
    ref: Optional[str] = None,
    request: Optional[Dict[str, Any]] = None,
    full_page: bool = False,
    image_type: str = "png",
    limit: int = 80,
    time_ms: Optional[int] = None,
    selector_state: Optional[str] = None,
    state: Optional[str] = None,
    text_gone: Optional[str] = None,
    url_contains: Optional[str] = None,
    load_state: Optional[str] = None,
    key: Optional[str] = None,
    values: Optional[List[str]] = None,
    delta_x: Optional[int] = None,
    delta_y: Optional[int] = None,
    **compat: Any,
) -> Dict[str, Any]:
    """
    Universal browser tool for web operations.

    Legacy operations are preserved (`navigate`, `click`, `type`, etc.) while new
    session-aware operations are available (`status`, `tabs`, `open`, `snapshot`,
    `act`, `console`, `network`).

    Args:
        operation: Browser operation to execute.
        url: URL used by `navigate`, `open`, `request`, and some action flows.
        selector: CSS selector target for element operations.
        text: Text payload for `type`, `click` text matching, and other operations.
        method: HTTP method for `request`.
        headers: Optional HTTP headers for `request`.
        body: Optional request body for `request`.
        query: Query text for `search`.
        timeout: Timeout in milliseconds.
        headless: Whether to run headless. Defaults to `False` (visible browser).
        profile: Browser profile/session key.
        target_id: Active tab target id.
        ref: Stable snapshot ref for element operations.
        request: Operation-specific payload for advanced/compound actions.
        full_page: Full-page screenshot flag.
        image_type: Screenshot image format (`png` or `jpeg`).
        limit: Result limit for list/snapshot/event operations.
        time_ms: Convenience wait duration.
        selector_state: Wait state for selector-based wait.
        state: Alias for wait selector state.
        text_gone: Text that should disappear during wait.
        url_contains: Substring expected in URL during wait.
        load_state: Page load state target for wait.
        key: Keyboard key for `press`.
        values: Option values for `select`.
        delta_x: Horizontal scroll delta.
        delta_y: Vertical scroll delta.
    """
    request_payload = _merge_request_payload(
        request=request,
        time_ms=time_ms,
        selector_state=selector_state,
        state=state,
        text_gone=text_gone,
        url_contains=url_contains,
        load_state=load_state,
        key=key,
        values=list(values) if values is not None else None,
        delta_x=delta_x,
        delta_y=delta_y,
        **compat,
    )
    service = get_browser_service()
    return await service.execute(
        operation=operation,
        url=url,
        selector=selector,
        text=text,
        method=method,
        headers=headers,
        body=body,
        query=query,
        timeout=timeout,
        headless=headless,
        profile=profile,
        target_id=target_id,
        ref=ref,
        request=request_payload,
        full_page=full_page,
        image_type=image_type,
        limit=limit,
    )


def _merge_request_payload(
    *,
    request: Optional[Dict[str, Any]],
    **compat: Any,
) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {}
    if isinstance(request, dict):
        payload.update(request)
    for key, value in compat.items():
        if value is None or key in payload:
            continue
        payload[key] = value
    return payload or None
