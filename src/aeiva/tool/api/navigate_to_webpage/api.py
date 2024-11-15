# navigate_to_webpage/api.py

from typing import Any, Dict
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

def navigate_to_webpage(url: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Navigates the browser to a specified webpage.

    Args:
        url (str): Full URL of the webpage to navigate to.
        timeout (int): Maximum time to wait for navigation to complete (in milliseconds).

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Validate required parameters
        if not url:
            return {
                "output": None,
                "error": "Missing required parameter: url",
                "error_code": "VALIDATION_ERROR"
            }

        # Initialize WebDriver (Chrome)
        driver = webdriver.Chrome()

        # Set page load timeout (in seconds)
        driver.set_page_load_timeout(timeout / 1000)

        try:
            driver.get(url)
        except WebDriverException as e:
            driver.quit()
            return {
                "output": None,
                "error": f"WebDriver Error: {e}",
                "error_code": "WEBDRIVER_ERROR"
            }

        driver.quit()

        return {
            "output": {"message": "Navigated to the specified webpage."},
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected Error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }