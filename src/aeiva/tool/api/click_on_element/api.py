# tools/click_on_element/api.py

from typing import Dict, Any
import pyautogui

def click_on_element(position: Dict[str, float]) -> Dict[str, Any]:
    """
    Clicks on a GUI element at a specified position.

    Args:
        position (dict): The position dictionary containing 'x', 'y', 'width', 'height'.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        required_keys = ['x', 'y', 'width', 'height']
        for key in required_keys:
            if key not in position:
                return {
                    "output": None,
                    "error": f"Missing key '{key}' in position dictionary.",
                    "error_code": "MISSING_POSITION_KEY"
                }

        x = position['x'] + position['width'] / 2
        y = position['y'] + position['height'] / 2

        if not (0 <= x <= pyautogui.size().width) or not (0 <= y <= pyautogui.size().height):
            return {
                "output": None,
                "error": f"Position ({x}, {y}) is out of screen bounds.",
                "error_code": "POSITION_OUT_OF_BOUNDS"
            }

        pyautogui.click(x, y)
        return {
            "output": f"Clicked on element at ({x}, {y}).",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error clicking on element: {e}",
            "error_code": "CLICK_ELEMENT_FAILED"
        }