# click_webpage_element/api.py

from typing import Any, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    WebDriverException
)
from pydantic import ValidationError
import json

def click_webpage_element(
    url: str,
    selector_type: str,
    selector: str,
    timeout: Optional[float] = 10.0
) -> Dict[str, Any]:
    """
    Simulates a click action on a specified element on the webpage. Ensures the element is visible and scrolls into view before clicking.

    Args:
        url (str): The URL of the webpage to interact with.
        selector_type (str): Type of selector to use (e.g., 'css', 'xpath', 'id', 'name', 'tag', 'class').
        selector (str): The selector value to locate the element on the webpage.
        timeout (float, optional): Maximum time to wait for the element to be present (in seconds). Defaults to 10.0.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Validate required parameters
        if not url or not selector_type or not selector:
            raise ValidationError("Missing required parameters.")

        # Initialize WebDriver (Example with Chrome)
        driver = webdriver.Chrome()

        # Set implicit wait
        driver.implicitly_wait(timeout)

        # Navigate to the desired URL
        driver.get(url)

        # Determine the selector type
        selector_mapping = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "tag": By.TAG_NAME,
            "class": By.CLASS_NAME
        }

        by = selector_mapping.get(selector_type)
        if not by:
            driver.quit()
            return {
                "output": None,
                "error": f"Unsupported selector type: {selector_type}",
                "error_code": "INVALID_SELECTOR_TYPE"
            }

        try:
            # Find the element
            element = driver.find_element(by, selector)
        except NoSuchElementException:
            driver.quit()
            return {
                "output": None,
                "error": "Element not found.",
                "error_code": "ELEMENT_NOT_FOUND"
            }

        try:
            # Scroll the element into view
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            scrolled = True
        except WebDriverException as e:
            driver.quit()
            return {
                "output": None,
                "error": f"Error scrolling to element: {e}",
                "error_code": "SCROLL_FAILED"
            }

        try:
            # Click the element
            element.click()
            driver.quit()
            result = {
                "success": True,
                "element_found": True,
                "scrolled_into_view": scrolled
            }
            return {
                "output": result,
                "error": None,
                "error_code": "SUCCESS"
            }
        except ElementNotInteractableException as e:
            driver.quit()
            result = {
                "success": False,
                "element_found": True,
                "scrolled_into_view": scrolled
            }
            return {
                "output": result,
                "error": f"Element not interactable: {e}",
                "error_code": "ELEMENT_NOT_INTERACTABLE"
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