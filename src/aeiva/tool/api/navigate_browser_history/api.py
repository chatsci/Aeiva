# navigate_browser_history/api.py

from typing import Any, Dict
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

def navigate_browser_history(direction: str, steps: int = 1) -> Dict[str, Any]:
    """
    Navigates the browser history either backward or forward by a specified number of steps.

    Args:
        direction (str): Direction to navigate: 'back' or 'forward'.
        steps (int): Number of steps to navigate in the specified direction.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Validate required parameters
        if direction not in ["back", "forward"]:
            return {
                "output": None,
                "error": f"Invalid direction: {direction}. Must be 'back' or 'forward'.",
                "error_code": "INVALID_DIRECTION"
            }

        if steps < 1:
            return {
                "output": None,
                "error": f"Invalid steps: {steps}. Must be >= 1.",
                "error_code": "INVALID_STEPS"
            }

        # Initialize WebDriver (Chrome)
        driver = webdriver.Chrome()

        # Perform navigation
        previous_url = driver.current_url
        try:
            for _ in range(steps):
                if direction == "back":
                    driver.back()
                else:
                    driver.forward()
        except WebDriverException as e:
            driver.quit()
            return {
                "output": None,
                "error": f"WebDriver Error during navigation: {e}",
                "error_code": "WEBDRIVER_ERROR"
            }

        new_url = driver.current_url
        driver.quit()

        message = f"Navigated {direction} by {steps} step(s)."

        return {
            "output": {
                "success": True,
                "previous_url": previous_url,
                "message": message
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