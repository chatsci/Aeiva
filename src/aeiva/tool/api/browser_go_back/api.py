# aeiva/tool/api/browser_go_back/api.py

import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

async def browser_go_back(
    context: BrowserContext,
    page_id: int
) -> Dict[str, Any]:
    """
    Go back in browser history on the specified page_id.

    Returns:
      {"result": {"page_id": <int>}, "error": <str>, "error_code": <str>}
    """
    try:
        page: Page = context.pages[page_id]
        await page.go_back()
        # Optionally wait for load
        await page.wait_for_load_state("domcontentloaded")

        return {
            "result": {"page_id": page_id},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to go back in history.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "BROWSER_GO_BACK_FAILED"
        }