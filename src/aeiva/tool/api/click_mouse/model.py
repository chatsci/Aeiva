# tools/click_mouse/model.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ClickMouseErrorCode:
    INVALID_BUTTON_TYPE = "INVALID_BUTTON_TYPE"
    INVALID_CLICKS = "INVALID_CLICKS"
    INVALID_INTERVAL = "INVALID_INTERVAL"
    CLICK_FAILED = "CLICK_FAILED"
    SUCCESS = "SUCCESS"

class ClickMouseParams(BaseModel):
    button: Optional[str] = Field("left", description="The mouse button to click ('left', 'right', 'middle').")
    clicks: Optional[int] = Field(1, description="Number of times to click.")
    interval: Optional[float] = Field(0.0, description="Interval between clicks in seconds.")

class ClickMouseResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")