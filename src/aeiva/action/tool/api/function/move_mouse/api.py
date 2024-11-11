# tools/move_mouse/api.py

import pyautogui
import time

def move_mouse(x: int, y: int, duration: float = 0.5) -> str:
    """
    Move the mouse cursor to a specific screen coordinate.

    Args:
        x (int): The x-coordinate on the screen.
        y (int): The y-coordinate on the screen.
        duration (float): Duration in seconds for the movement.

    Returns:
        str: A message indicating the result.
    """
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return f"Mouse moved to ({x}, {y}) over {duration} seconds."
    except Exception as e:
        return f"Error moving mouse: {e}"