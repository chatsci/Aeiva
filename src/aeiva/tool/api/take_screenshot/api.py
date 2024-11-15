# tools/take_screenshot/api.py

from typing import Dict, Any
import pyautogui
import os
from datetime import datetime
from dotenv import load_dotenv

def take_screenshot(save_path: str = None) -> Dict[str, Any]:
    """
    Captures the current screen.

    Args:
        save_path (str, optional): The path to save the screenshot image. If not provided, saves to 'AI_ACCESSIBLE_PATH' with a timestamped filename.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        # Load environment variables
        load_dotenv()
        SAVE_PATH = os.getenv('AI_ACCESSIBLE_PATH')

        screenshot = pyautogui.screenshot()

        if save_path is None:
            if not SAVE_PATH:
                return {
                    "output": None,
                    "error": "SAVE_PATH is not set in environment variables.",
                    "error_code": "MISSING_SAVE_PATH"
                }
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.expanduser(f"{SAVE_PATH}/screenshot_{timestamp}.png")
        else:
            save_path = os.path.expanduser(save_path)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        screenshot.save(save_path)

        return {
            "output": f"Screenshot saved to {save_path}",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error taking screenshot: {e}",
            "error_code": "TAKE_SCREENSHOT_FAILED"
        }