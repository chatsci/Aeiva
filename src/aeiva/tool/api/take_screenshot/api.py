# tools/take_screenshot/api.py

from typing import Dict, Any
from datetime import datetime
from pathlib import Path

import pyautogui

def take_screenshot(save_path: str = None) -> Dict[str, Any]:
    """
    Captures the current screen.

    Args:
        save_path (str, optional): The path to save the screenshot image. If not provided, saves under storage/screenshots with a timestamped filename.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        screenshot = pyautogui.screenshot()

        if save_path is None:
            default_dir = Path.cwd() / "storage" / "screenshots"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = default_dir / f"screenshot_{timestamp}.png"
        else:
            save_path = Path(save_path).expanduser()

        # Ensure the directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        screenshot.save(str(save_path))

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
