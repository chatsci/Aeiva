# tools/move_mouse/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class MoveMouseErrorCode:
    INVALID_DURATION = "INVALID_DURATION"
    COORDINATES_OUT_OF_BOUNDS = "COORDINATES_OUT_OF_BOUNDS"
    MOVE_MOUSE_FAILED = "MOVE_MOUSE_FAILED"
    SUCCESS = "SUCCESS"

class MoveMouseParams(BaseModel):
    x: int = Field(..., description="The x-coordinate on the screen.")
    y: int = Field(..., description="The y-coordinate on the screen.")
    duration: Optional[float] = Field(0.5, description="Duration in seconds for the movement.")

class MoveMouseResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")