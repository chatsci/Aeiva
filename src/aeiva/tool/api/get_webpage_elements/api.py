# get_webpage_elements/api.py

from typing import Any, Dict, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from pydantic import ValidationError
import json

def get_webpage_elements(
    url: str,
    selector_type: str,
    selector: str,
    timeout: Optional[float] = 10.0
) -> Dict[str, Any]:
    """
    Retrieves details of all elements matching the given selector on the current webpage.

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

        # Find elements
        elements = driver.find_elements(by, selector)

        if not elements:
            driver.quit()
            return {
                "output": [],
                "error": "No elements found matching the selector.",
                "error_code": "NO_ELEMENTS_FOUND"
            }

        # Extract details from each element
        elements_details = []
        for elem in elements:
            try:
                attributes = {}
                for attr in elem.get_property('attributes'):
                    attributes[attr['name']] = attr['value']

                details = {
                    "tag_name": elem.tag_name,
                    "id": elem.get_attribute("id"),
                    "class": elem.get_attribute("class"),
                    "text": elem.text,
                    "attributes": attributes
                }
                elements_details.append(details)
            except WebDriverException:
                continue  # Skip elements that cause errors

        driver.quit()

        return {
            "output": elements_details,
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