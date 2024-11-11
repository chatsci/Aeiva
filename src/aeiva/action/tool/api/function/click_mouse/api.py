# tools/click_mouse/api.py

import pyautogui

def click_mouse(button: str = "left", clicks: int = 1, interval: float = 0.0) -> str:
    """
    Perform mouse click actions.

    Args:
        button (str): The button to click ('left', 'right', 'middle').
        clicks (int): Number of times to click.
        interval (float): Interval between clicks in seconds.

    Returns:
        str: A message indicating the result.
    """
    try:
        pyautogui.click(button=button, clicks=clicks, interval=interval)
        return f"Mouse clicked {clicks} time(s) with {button} button."
    except Exception as e:
        return f"Error clicking mouse: {e}"