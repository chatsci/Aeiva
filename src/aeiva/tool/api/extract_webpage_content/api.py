import logging
from typing import Dict, Any, Literal
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

async def extract_webpage_content(
    context: BrowserContext,
    page_id: int,
    format: Literal["text", "html"] = "text"
) -> Dict[str, Any]:
    """
    Extract the webpage content as text or raw HTML.
    """
    try:
        page: Page = context.pages[page_id]
        raw_html = await page.content()

        if format == "html":
            content = raw_html
        else:
            # naive text approach
            # you might want a more robust HTML->text conversion
            content = raw_html

        return {
            "result": {"format": format, "content": content},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to extract content.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "EXTRACT_CONTENT_FAILED"
        }