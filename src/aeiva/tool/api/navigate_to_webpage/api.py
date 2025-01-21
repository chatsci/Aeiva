import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

async def navigate_to_webpage(
    context: BrowserContext,
    page_id: int,
    url: str
) -> Dict[str, Any]:
    """
    Navigate an existing page to the given URL.
    """
    if not url:
        return {
            "result": None,
            "error": "URL must not be empty.",
            "error_code": "VALIDATION_ERROR"
        }
    try:
        page: Page = context.pages[page_id]
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        return {
            "result": {"page_id": page_id, "url": url},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to navigate to webpage.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "NAVIGATE_FAILED"
        }