# refresh_webpage/api.py

from typing import Any, Dict
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

def refresh_webpage(ignore_cache: bool = False) -> Dict[str, Any]:
    """
    Refreshes the current page in the browser, optionally ignoring the browser cache.

    Args:
        ignore_cache (bool): Whether to ignore the browser cache when refreshing.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Initialize WebDriver (Chrome)
        driver = webdriver.Chrome()

        # Get previous URL
        previous_url = driver.current_url

        # Perform refresh
        try:
            if ignore_cache:
                driver.execute_script("location.reload();")
            else:
                driver.refresh()
        except WebDriverException as e:
            driver.quit()
            return {
                "output": None,
                "error": f"WebDriver Error during refresh: {e}",
                "error_code": "WEBDRIVER_ERROR"
            }

        # Get new URL
        new_url = driver.current_url
        driver.quit()

        return {
            "output": {
                "success": True,
                "previous_url": previous_url,
                "new_url": new_url if new_url != previous_url else None
            },
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected Error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }