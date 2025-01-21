import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page, ElementHandle

logger = logging.getLogger(__name__)

async def click_webpage_element(
    context: BrowserContext,
    page_id: int,
    selector: str
) -> Dict[str, Any]:
    """
    Click an element by CSS selector on the specified page.
    """
    try:
        page: Page = context.pages[page_id]
        element: ElementHandle = await page.query_selector(selector)
        if not element:
            return {
                "result": None,
                "error": f"No element found for selector '{selector}'",
                "error_code": "ELEMENT_NOT_FOUND"
            }

        await element.click()
        return {
            "result": {"page_id": page_id, "selector": selector},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to click element.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "CLICK_FAILED"
        }