import logging
from typing import Dict, Any
from playwright.async_api import BrowserContext, Page, ElementHandle

logger = logging.getLogger(__name__)

async def upload_file_on_webpage(
    context: BrowserContext,
    page_id: int,
    selector: str,
    file_path: str
) -> Dict[str, Any]:
    """
    Upload a file by setting input[type=file] to file_path.
    """
    try:
        page: Page = context.pages[page_id]
        element: ElementHandle = await page.query_selector(selector)
        if not element:
            return {
                "result": None,
                "error": f"No element for selector {selector}",
                "error_code": "ELEMENT_NOT_FOUND"
            }

        await element.set_input_files(file_path)
        return {
            "result": {"page_id": page_id, "selector": selector, "file_path": file_path},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        logger.exception("Failed to upload file.")
        return {
            "result": None,
            "error": str(e),
            "error_code": "UPLOAD_FILE_FAILED"
        }