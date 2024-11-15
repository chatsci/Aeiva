# tools/take_screenshot/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class TakeScreenshotErrorCode:
    MISSING_SAVE_PATH = "MISSING_SAVE_PATH"
    TAKE_SCREENSHOT_FAILED = "TAKE_SCREENSHOT_FAILED"
    SUCCESS = "SUCCESS"

class TakeScreenshotParams(BaseModel):
    save_path: Optional[str] = Field(None, description="The path to save the screenshot image. If not provided, saves to 'AI_ACCESSIBLE_PATH' with a timestamped filename.")

class TakeScreenshotResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")