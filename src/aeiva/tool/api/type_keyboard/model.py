# tools/type_keyboard/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class TypeKeyboardErrorCode:
    MISSING_TEXT = "MISSING_TEXT"
    INVALID_INTERVAL = "INVALID_INTERVAL"
    TYPE_KEYBOARD_FAILED = "TYPE_KEYBOARD_FAILED"
    SUCCESS = "SUCCESS"

class TypeKeyboardParams(BaseModel):
    text: str = Field(..., description="The text to type.")
    interval: Optional[float] = Field(0.05, description="Time interval between each character.")

class TypeKeyboardResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")