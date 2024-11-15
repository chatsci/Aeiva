# tools/click_on_element/model.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ClickOnElementErrorCode:
    MISSING_POSITION_KEY = "MISSING_POSITION_KEY"
    POSITION_OUT_OF_BOUNDS = "POSITION_OUT_OF_BOUNDS"
    CLICK_ELEMENT_FAILED = "CLICK_ELEMENT_FAILED"
    SUCCESS = "SUCCESS"

class ClickOnElementParams(BaseModel):
    position: Dict[str, float] = Field(..., description="The position dictionary containing 'x', 'y', 'width', 'height'.")

class ClickOnElementResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")