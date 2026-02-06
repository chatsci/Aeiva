"""
Browser Tool: Universal web interaction.

Browser V2 adds persistent profiles/tabs and deterministic snapshot+ref actions,
while preserving the legacy operation-style API.
"""

from typing import Any, Dict, Optional

from ..capability import Capability
from ..decorator import tool
from ._browser_service import get_browser_service


@tool(
    description=(
        "Perform browser operations: status, start, stop, profiles, tabs, open, focus, close, "
        "navigate, back, forward, reload, click, type, press, hover, select, drag, scroll, upload, "
        "wait, evaluate, snapshot, act, screenshot, pdf, get_text, get_html, console, errors, "
        "network, request, search"
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
    timeout: int = 30000,
    headless: bool = False,
    profile: str = "default",
    target_id: Optional[str] = None,
    ref: Optional[str] = None,
    request: Optional[Dict[str, Any]] = None,
    full_page: bool = False,
    image_type: str = "png",
    limit: int = 80,
) -> Dict[str, Any]:
    """
    Universal browser tool for web operations.

    Legacy operations are preserved (`navigate`, `click`, `type`, etc.) while new
    session-aware operations are available (`status`, `tabs`, `open`, `snapshot`,
    `act`, `console`, `network`).
    """
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
        request=request,
        full_page=full_page,
        image_type=image_type,
        limit=limit,
    )
