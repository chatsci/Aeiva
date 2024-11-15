# execute_js_script_on_webpage/api.py

from typing import Any, Dict, Optional, List
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from pydantic import ValidationError
import json

def execute_js_script_on_webpage(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a custom JavaScript script within the context of the current webpage. Optionally, pass arguments to the script.

    Args:
        request (Dict[str, Any]): A dictionary containing the request parameters.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Extract parameters from the request
        url = request.get("url")
        script = request.get("script")
        args = request.get("args", [])

        # Validate required parameters
        if not url or not script:
            raise ValidationError("Missing required parameters.")

        # Initialize WebDriver (Example with Chrome)
        driver = webdriver.Chrome()

        # Navigate to the desired URL
        driver.get(url)

        try:
            # Execute the custom JavaScript with optional arguments
            result = driver.execute_script(script, *args)
        except WebDriverException as e:
            driver.quit()
            return {
                "output": None,
                "error": f"JavaScript Execution Error: {e}",
                "error_code": "JS_EXECUTION_ERROR"
            }

        driver.quit()

        return {
            "output": {"result": result},
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