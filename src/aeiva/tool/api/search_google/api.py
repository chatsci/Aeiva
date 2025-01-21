# aeiva/tool/api/search_google/api.py

import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page
import urllib.parse

logger = logging.getLogger(__name__)

async def search_google(
    context: BrowserContext,
    page_id: int,
    query: str
) -> Dict[str, Any]:
    """
    Uses direct Google search URL:
      https://www.google.com/search?q=<query>

    - If your IP or environment triggers reCAPTCHA, you can solve it manually once
      if you're using a persistent context in headful mode.
    - If there's a cookie banner or 'Accept all' button, you can click it manually too.

    Returns:
       {
         "result": {"page_id": page_id, "query": query},
         "error": str | None,
         "error_code": "SUCCESS" | "SEARCH_GOOGLE_FAILED"
       }
    """
    try:
        page: Page = context.pages[page_id]

        # 1) Encode the query
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded_query}"

        # 2) Go to the direct search URL
        await page.goto(search_url)
        await page.wait_for_load_state("domcontentloaded")

        # Optionally, you can try to detect & click any cookie banner if needed:
        # e.g. 
        # try:
        #     await page.click('button[aria-label="Accept all"]', timeout=3000)
        # except:
        #     pass

        return {
            "result": {"page_id": page_id, "query": query},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to search on Google.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "SEARCH_GOOGLE_FAILED"
        }