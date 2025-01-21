import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

async def scroll_webpage(
    context: BrowserContext,
    page_id: int,
    x: int = 0,
    y: int = 1000
) -> Dict[str, Any]:
    """
    Scroll the page by (x, y) offsets.
    """
    try:
        page: Page = context.pages[page_id]
        await page.evaluate(f"window.scrollBy({x}, {y})")
        return {
            "result": {"page_id": page_id, "scroll_x": x, "scroll_y": y},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to scroll page.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "SCROLL_FAILED"
        }