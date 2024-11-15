# type_text_in_webpage_element/api.py

from typing import Any, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException

def type_text_in_webpage_element(selector: str, text: str, selector_type: str = "css", clear_existing: bool = False) -> Dict[str, Any]:
    """
    Types text into a specified element on the webpage.

    Args:
        selector (str): Selector value of the target element.
        text (str): Text to type into the element.
        selector_type (str): Type of selector to use (e.g., 'css', 'xpath', 'id', 'name', 'tag', 'class').
        clear_existing (bool): Whether to clear existing text before typing.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not text:
            return {
                "output": None,
                "error": "Missing required parameter: text",
                "error_code": "VALIDATION_ERROR"
            }

        driver = webdriver.Chrome()

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
            element = driver.find_element(by, selector)
        except NoSuchElementException:
            driver.quit()
            return {
                "output": None,
                "error": "Element not found.",
                "error_code": "ELEMENT_NOT_FOUND"
            }
        except WebDriverException as e:
            driver.quit()
            return {
                "output": None,
                "error": f"WebDriver Error during finding element: {e}",
                "error_code": "WEBDRIVER_ERROR"
            }

        driver.execute_script("arguments[0].scrollIntoView();", element)

        if clear_existing:
            try:
                element.clear()
            except WebDriverException as e:
                driver.quit()
                return {
                    "output": None,
                    "error": f"WebDriver Error during clearing text: {e}",
                    "error_code": "WEBDRIVER_ERROR"
                }

        try:
            element.send_keys(text)
        except WebDriverException as e:
            driver.quit()
            return {
                "output": None,
                "error": f"WebDriver Error during typing text: {e}",
                "error_code": "WEBDRIVER_ERROR"
            }

        final_value = element.get_attribute("value") or element.text
        driver.quit()

        return {
            "output": {
                "success": True,
                "element_found": True,
                "text_typed": text,
                "final_element_value": final_value
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