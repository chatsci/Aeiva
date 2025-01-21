# aeiva/tool/api/open_url/api.py

import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

async def open_url(
    context: BrowserContext,
    url: str
) -> Dict[str, Any]:
    """
    Opens a new browser page in the given BrowserContext and navigates to `url`.

    Returns a standard dictionary:
      {
        "result": {"page_id": <int>, "opened_url": <str>},
        "error": <str|None>,
        "error_code": <str>
      }
    """
    try:
        # Create a new page in the context
        page: Page = await context.new_page()
        page_id = len(context.pages) - 1  # newly created page is last

        if not url:
            return {
                "result": None,
                "error": "URL is empty or not provided",
                "error_code": "URL_NOT_PROVIDED"
            }

        # Navigate
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")

        return {
            "result": {
                "page_id": page_id,
                "opened_url": url
            },
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("[open_url] Failed to open new page with given URL.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "OPEN_URL_FAILED"
        }