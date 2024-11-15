# scroll_webpage/api.py

from typing import Any, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException

def scroll_webpage(selector: str = None, selector_type: str = "css", scroll_type: str = "pixels", direction: str = "down", amount: int = 200) -> Dict[str, Any]:
    """
    Scrolls the page in the browser either by a specified number of pixels or to a specific element.

    Args:
        selector (str): Selector value of the element to interact with.
        selector_type (str): Type of selector to use (e.g., 'css', 'xpath', 'id', 'name', 'tag', 'class').
        scroll_type (str): Type of scroll action: 'pixels' or 'element'.
        direction (str): Direction to scroll: 'up', 'down', 'left', or 'right'.
        amount (int): Number of pixels to scroll (required for 'pixels' scroll type).

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if scroll_type not in ["pixels", "element"]:
            return {
                "output": None,
                "error": f"Invalid scroll_type: {scroll_type}. Must be 'pixels' or 'element'.",
                "error_code": "INVALID_SCROLL_TYPE"
            }

        if direction not in ["up", "down", "left", "right"]:
            return {
                "output": None,
                "error": f"Invalid direction: {direction}. Must be 'up', 'down', 'left', or 'right'.",
                "error_code": "INVALID_DIRECTION"
            }

        driver = webdriver.Chrome()

        if scroll_type == "pixels":
            try:
                if direction == "up":
                    driver.execute_script(f"window.scrollBy(0, -{amount});")
                elif direction == "down":
                    driver.execute_script(f"window.scrollBy(0, {amount});")
                elif direction == "left":
                    driver.execute_script(f"window.scrollBy(-{amount}, 0);")
                elif direction == "right":
                    driver.execute_script(f"window.scrollBy({amount}, 0);")
            except WebDriverException as e:
                driver.quit()
                return {
                    "output": None,
                    "error": f"WebDriver Error during scrolling: {e}",
                    "error_code": "WEBDRIVER_ERROR"
                }

            driver.quit()
            return {
                "output": {"success": True, "scrolled_amount": amount},
                "error": None,
                "error_code": "SUCCESS"
            }

        elif scroll_type == "element":
            if not selector:
                driver.quit()
                return {
                    "output": None,
                    "error": "Selector must be provided for 'element' scroll_type.",
                    "error_code": "MISSING_SELECTOR"
                }

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
                    "error": f"Element not found with selector: {selector}",
                    "error_code": "ELEMENT_NOT_FOUND"
                }
            except WebDriverException as e:
                driver.quit()
                return {
                    "output": None,
                    "error": f"WebDriver Error during finding element: {e}",
                    "error_code": "WEBDRIVER_ERROR"
                }

            try:
                driver.execute_script("arguments[0].scrollIntoView();", element)
            except WebDriverException as e:
                driver.quit()
                return {
                    "output": None,
                    "error": f"WebDriver Error during scrolling to element: {e}",
                    "error_code": "WEBDRIVER_ERROR"
                }

            driver.quit()
            return {
                "output": {"success": True, "element_found": True},
                "error": None,
                "error_code": "SUCCESS"
            }

    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected Error: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }