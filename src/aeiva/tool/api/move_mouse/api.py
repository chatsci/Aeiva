# tools/move_mouse/api.py

from typing import Dict, Any
import pyautogui

def move_mouse(x: int, y: int, duration: float = 0.5) -> Dict[str, Any]:
    """
    Moves the mouse cursor to a specific screen coordinate.

    Args:
        x (int): The x-coordinate on the screen.
        y (int): The y-coordinate on the screen.
        duration (float, optional): Duration in seconds for the movement. Defaults to 0.5.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if duration < 0:
            return {
                "output": None,
                "error": "Duration cannot be negative.",
                "error_code": "INVALID_DURATION"
            }
        
        screen_width, screen_height = pyautogui.size()
        if not (0 <= x <= screen_width) or not (0 <= y <= screen_height):
            return {
                "output": None,
                "error": f"Coordinates ({x}, {y}) are out of screen bounds.",
                "error_code": "COORDINATES_OUT_OF_BOUNDS"
            }

        pyautogui.moveTo(x, y, duration=duration)
        return {
            "output": f"Mouse moved to ({x}, {y}) over {duration} seconds.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error moving mouse: {e}",
            "error_code": "MOVE_MOUSE_FAILED"
        }