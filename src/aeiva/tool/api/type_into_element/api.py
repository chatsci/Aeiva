# tools/type_into_element/api.py

from typing import Dict, Any
import pyautogui

def type_into_element(position: dict, text: str) -> Dict[str, Any]:
    """
    Clicks on an input field and types text.

    Args:
        position (dict): The position dictionary containing 'x', 'y', 'width', 'height'.
        text (str): The text to type into the input field.

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

        screen_width, screen_height = pyautogui.size()
        if not (0 <= x <= screen_width) or not (0 <= y <= screen_height):
            return {
                "output": None,
                "error": f"Coordinates ({x}, {y}) are out of screen bounds.",
                "error_code": "POSITION_OUT_OF_BOUNDS"
            }

        pyautogui.click(x, y)
        pyautogui.write(text, interval=0.05)

        return {
            "output": f"Typed into element at ({x}, {y}).",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error typing into element: {e}",
            "error_code": "TYPE_INTO_ELEMENT_FAILED"
        }