# get_webpage_details/api.py

from typing import Any, Dict, Optional, List
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from pydantic import ValidationError
import json

def get_webpage_details(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves comprehensive details about the current webpage, including title, URL, meta tags, and optionally, an accessibility snapshot.

    Args:
        request (Dict[str, Any]): A dictionary containing the request parameters.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Extract parameters from the request
        url = request.get("url")
        include_accessibility = request.get("include_accessibility", True)

        # Validate required parameters
        if not url:
            raise ValidationError("Missing required parameter: url.")

        # Initialize WebDriver (Example with Chrome)
        driver = webdriver.Chrome()

        # Navigate to the desired URL
        driver.get(url)

        # Execute JavaScript to get page details
        page_details = driver.execute_script(
            """
            return {
                title: document.title,
                url: window.location.href,
                metaTags: Array.from(document.getElementsByTagName('meta')).map(meta => ({
                    name: meta.getAttribute('name'),
                    content: meta.getAttribute('content')
                })),
                accessibilitySnapshot: arguments[0] ? window.accessibilitySnapshot || null : null
            };
            """,
            include_accessibility
        )

        if not include_accessibility:
            page_details.pop("accessibilitySnapshot", None)

        driver.quit()

        return {
            "output": page_details,
            "error": None,
            "error_code": "SUCCESS"
        }

    except ValidationError as ve:
        return {
            "output": None,
            "error": f"Validation Error: {ve}",
            "error_code": "VALIDATION_ERROR"
        }
    except WebDriverException as we:
        return {
            "output": None,
            "error": f"WebDriver Error: {we}",
            "error_code": "WEBDRIVER_ERROR"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected Error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }