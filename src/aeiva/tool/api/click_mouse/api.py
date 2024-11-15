# tools/click_mouse/api.py

from typing import Dict, Any
import pyautogui

def click_mouse(button: str = "left", clicks: int = 1, interval: float = 0.0) -> Dict[str, Any]:
    """
    Perform mouse click actions.

    Args:
        button (str): The button to click ('left', 'right', 'middle').
        clicks (int): Number of times to click.
        interval (float): Interval between clicks in seconds.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if button not in ['left', 'right', 'middle']:
            return {
                "output": None,
                "error": f"Invalid button type: {button}. Choose from 'left', 'right', or 'middle'.",
                "error_code": "INVALID_BUTTON_TYPE"
            }
        
        if clicks < 1:
            return {
                "output": None,
                "error": "Number of clicks must be at least 1.",
                "error_code": "INVALID_CLICKS"
            }
        
        if interval < 0:
            return {
                "output": None,
                "error": "Interval between clicks cannot be negative.",
                "error_code": "INVALID_INTERVAL"
            }

        pyautogui.click(button=button, clicks=clicks, interval=interval)
        return {
            "output": f"Mouse clicked {clicks} time(s) with {button} button.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error clicking mouse: {e}",
            "error_code": "CLICK_FAILED"
        }