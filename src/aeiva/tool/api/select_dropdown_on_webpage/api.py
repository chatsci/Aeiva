import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

async def select_dropdown_on_webpage(
    context: BrowserContext,
    page_id: int,
    selector: str,
    value: str
) -> Dict[str, Any]:
    """
    Select an option in a dropdown by value.
    """
    try:
        page: Page = context.pages[page_id]
        await page.select_option(selector, value=value)
        return {
            "result": {"page_id": page_id, "selector": selector, "value": value},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to select dropdown option.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "SELECT_DROPDOWN_FAILED"
        }