import logging
from typing import Dict, Any, List
from playwright.async_api import BrowserContext, Page, ElementHandle

logger = logging.getLogger(__name__)

async def send_keys_on_webpage(
    context: BrowserContext,
    page_id: int,
    selector: str,
    keys: List[str]
) -> Dict[str, Any]:
    """
    Send a series of key presses to an element or the page (if selector is blank).
    Example: keys = ["Tab", "Enter", "ArrowDown"]
    """
    try:
        page: Page = context.pages[page_id]

        if selector:
            element: ElementHandle = await page.query_selector(selector)
            if not element:
                return {
                    "result": None,
                    "error": f"No element found for '{selector}'",
                    "error_code": "ELEMENT_NOT_FOUND"
                }
            await element.click(force=True)  # focus on it if needed
        else:
            # No selector means just send keys to the page
            await page.click("body", force=True)

        for k in keys:
            await page.keyboard.press(k)

        return {
            "result": {"page_id": page_id, "selector": selector, "keys": keys},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to send keys.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "SEND_KEYS_FAILED"
        }