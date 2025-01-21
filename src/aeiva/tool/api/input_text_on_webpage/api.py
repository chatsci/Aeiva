import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page, ElementHandle

logger = logging.getLogger(__name__)

async def input_text_on_webpage(
    context: BrowserContext,
    page_id: int,
    selector: str,
    text: str
) -> Dict[str, Any]:
    """
    Locate an input/text area by selector, fill it with the given text.
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

        await element.fill(text)  # or element.type(text)
        return {
            "result": {"page_id": page_id, "selector": selector, "typed_text": text},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to input text.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "INPUT_TEXT_FAILED"
        }