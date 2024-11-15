# tools/scroll/api.py

from typing import Dict, Any, Optional
import pyautogui

def scroll(
    direction: str = "down",
    lines: int = 100,
    scroll_id: int = 0
) -> Dict[str, Any]:
    """
    Scrolls the view up or down by a specified number of lines.

    Args:
        direction (str, optional): The direction to scroll: 'up' or 'down'. Defaults to 'down'.
        lines (int, optional): Number of lines to scroll by. Must be between 1 and 1000. Defaults to 100.
        scroll_id (int, optional): Unique ID for each scroll request. Defaults to 0.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Validate direction
        if direction.lower() not in ["up", "down"]:
            return {
                "output": None,
                "error": "Invalid direction. Choose 'up' or 'down'.",
                "error_code": "INVALID_DIRECTION"
            }
        
        # Validate lines
        if not (1 <= lines <= 1000):
            return {
                "output": None,
                "error": "Lines must be between 1 and 1000.",
                "error_code": "INVALID_LINES"
            }
        
        # Calculate scroll amount
        scroll_amount = lines if direction.lower() == "up" else -lines
        
        # Perform scrolling
        pyautogui.scroll(scroll_amount)
        
        return {
            "output": f"Scrolled {direction} by {lines} lines. Scroll ID: {scroll_id}",
            "error": None,
            "error_code": "SUCCESS"
        }
    
    except Exception as e:
        return {
            "output": None,
            "error": f"Error during scrolling: {e}",
            "error_code": "SCROLL_FAILED"
        }