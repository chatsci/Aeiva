import logging
from typing import Dict, Any, Optional
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

async def open_browser_tab(
    context: BrowserContext,
    url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Opens a new tab (page). If url is provided, navigates to it.
    The new page's index = len(context.pages) - 1 after creation.
    """
    try:
        page: Page = await context.new_page()
        new_page_id = len(context.pages) - 1  # The new page is last
        if url:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")

        return {
            "result": {"page_id": new_page_id, "opened_url": url},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to open new tab.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "OPEN_TAB_FAILED"
        }