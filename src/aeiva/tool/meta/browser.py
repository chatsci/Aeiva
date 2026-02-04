"""
Browser Tool: Universal web interaction.

One meta tool for ALL web operations - navigate, click, type, scrape, search, request, etc.
"""

import base64
from typing import Any, Dict, Optional

from ..decorator import tool
from ..capability import Capability


@tool(
    description="Perform web operations: navigate, click, type, screenshot, get_text, get_html, request, search",
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
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Universal browser tool for all web operations.

    Args:
        operation: Operation: navigate, click, type, screenshot, get_text, get_html, request, search.
        url: URL for navigate/request operations.
        selector: CSS selector for element operations (click, type, get_text).
        text: Text to type (for type operation) or search query alias.
        method: HTTP method for request operation (GET, POST, PUT, DELETE).
        headers: HTTP headers for request operation.
        body: Request body for request operation.
        query: Search query (for search operation).
        timeout: Operation timeout in milliseconds.
        headless: Run browser in headless mode.

    Returns:
        Dictionary with operation result or error.
    """
    operations = {
        "navigate": _navigate,
        "click": _click,
        "type": _type,
        "screenshot": _screenshot,
        "get_text": _get_text,
        "get_html": _get_html,
        "request": _request,
        "search": _search,
    }

    if operation not in operations:
        return {
            "success": False,
            "error": f"Unknown operation: {operation}. Valid: {list(operations.keys())}",
        }

    try:
        return await operations[operation](
            url=url,
            selector=selector,
            text=text,
            method=method,
            headers=headers,
            body=body,
            query=query,
            timeout=timeout,
            headless=headless,
        )
    except ImportError as e:
        return {"success": False, "error": f"Missing dependency: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _navigate(url: str, timeout: int, headless: bool, **_) -> Dict[str, Any]:
    """Navigate to URL and return page info."""
    if not url:
        return {"success": False, "error": "URL required for navigate operation"}

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url, timeout=timeout)
        title = await page.title()
        current_url = page.url
        await browser.close()

    return {"success": True, "url": current_url, "title": title, "error": None}


async def _click(url: str, selector: str, timeout: int, headless: bool, **_) -> Dict[str, Any]:
    """Click an element on a page."""
    if not selector:
        return {"success": False, "error": "Selector required for click operation"}

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        if url:
            await page.goto(url, timeout=timeout)
        await page.click(selector, timeout=timeout)
        result_url = page.url
        await browser.close()

    return {"success": True, "clicked": selector, "url": result_url, "error": None}


async def _type(url: str, selector: str, text: str, timeout: int, headless: bool, **_) -> Dict[str, Any]:
    """Type text into an element."""
    if not selector:
        return {"success": False, "error": "Selector required for type operation"}
    if text is None:
        return {"success": False, "error": "Text required for type operation"}

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        if url:
            await page.goto(url, timeout=timeout)
        await page.fill(selector, text, timeout=timeout)
        await browser.close()

    return {"success": True, "typed_into": selector, "error": None}


async def _screenshot(url: str, timeout: int, headless: bool, **_) -> Dict[str, Any]:
    """Take a screenshot of the page."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        if url:
            await page.goto(url, timeout=timeout)
        screenshot = await page.screenshot()
        await browser.close()

    return {
        "success": True,
        "screenshot": base64.b64encode(screenshot).decode("utf-8"),
        "format": "base64",
        "mime_type": "image/png",
        "error": None,
    }


async def _get_text(url: str, selector: Optional[str], timeout: int, headless: bool, **_) -> Dict[str, Any]:
    """Get text content from page or element."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        if url:
            await page.goto(url, timeout=timeout)
        if selector:
            text = await page.text_content(selector, timeout=timeout)
        else:
            text = await page.inner_text("body")
        await browser.close()

    return {"success": True, "text": text, "error": None}


async def _get_html(url: str, selector: Optional[str], timeout: int, headless: bool, **_) -> Dict[str, Any]:
    """Get HTML content from page or element."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        if url:
            await page.goto(url, timeout=timeout)
        if selector:
            html = await page.inner_html(selector)
        else:
            html = await page.content()
        await browser.close()

    return {"success": True, "html": html, "error": None}


async def _request(
    url: str,
    method: str,
    headers: Optional[Dict[str, str]],
    body: Optional[str],
    timeout: int,
    **_
) -> Dict[str, Any]:
    """Make HTTP request (without browser)."""
    if not url:
        return {"success": False, "error": "URL required for request operation"}

    import aiohttp

    timeout_sec = timeout / 1000
    async with aiohttp.ClientSession() as session:
        kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout_sec)}
        if headers:
            kwargs["headers"] = headers
        if body and method in ("POST", "PUT", "PATCH"):
            kwargs["data"] = body

        async with session.request(method, url, **kwargs) as response:
            try:
                response_body = await response.text()
            except Exception:
                response_body = await response.read()
                response_body = response_body.decode("utf-8", errors="replace")

            return {
                "success": True,
                "status": response.status,
                "headers": dict(response.headers),
                "body": response_body,
                "error": None,
            }


async def _search(query: str, text: str, **_) -> Dict[str, Any]:
    """Search the web using DuckDuckGo."""
    search_query = query or text
    if not search_query:
        return {"success": False, "error": "Query required for search operation"}

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=10))

        return {
            "success": True,
            "query": search_query,
            "results": results,
            "error": None,
        }
    except ImportError:
        return {
            "success": False,
            "error": "duckduckgo-search not installed. Run: pip install duckduckgo-search",
        }
