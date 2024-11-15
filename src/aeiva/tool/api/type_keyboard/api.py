# tools/type_keyboard/api.py

from typing import Dict, Any
import pyautogui

def type_keyboard(text: str, interval: float = 0.05) -> Dict[str, Any]:
    """
    Simulates keyboard typing to input text.

    Args:
        text (str): The text to type.
        interval (float, optional): Time interval between each character. Defaults to 0.05.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not text:
            return {
                "output": None,
                "error": "Text to type must be provided.",
                "error_code": "MISSING_TEXT"
            }
        
        if interval < 0:
            return {
                "output": None,
                "error": "Interval cannot be negative.",
                "error_code": "INVALID_INTERVAL"
            }

        pyautogui.write(text, interval=interval)
        return {
            "output": f"Typed text: '{text}'",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error typing text: {e}",
            "error_code": "TYPE_KEYBOARD_FAILED"
        }