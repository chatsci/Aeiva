import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)

async def close_browser_tab(
    context: BrowserContext,
    page_id: int
) -> Dict[str, Any]:
    """
    Close the given page (tab) in the BrowserContext.
    """
    try:
        page = context.pages[page_id]
        await page.close()
        return {
            "result": {"closed_page_id": page_id},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to close browser tab.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "CLOSE_TAB_FAILED"
        }