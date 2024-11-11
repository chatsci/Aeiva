# tools/take_screenshot/api.py

import pyautogui
import os
from datetime import datetime
from dotenv import load_dotenv

SAVE_PATH = os.getenv('AI_ACCESSIBLE_PATH')

def take_screenshot(save_path: str = None) -> str:
    """
    Capture the current screen.

    Args:
        save_path (str): The path to save the screenshot image.

    Returns:
        str: A message indicating the result.
    """
    try:
        screenshot = pyautogui.screenshot()
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.expanduser(f"{SAVE_PATH}/screenshot_{timestamp}.png")
        else:
            save_path = os.path.expanduser(save_path)
        screenshot.save(save_path)
        return f"Screenshot saved to {save_path}"
    except Exception as e:
        return f"Error taking screenshot: {e}"