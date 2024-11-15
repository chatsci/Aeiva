# tools/scroll/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ScrollErrorCode:
    INVALID_DIRECTION = "INVALID_DIRECTION"
    INVALID_LINES = "INVALID_LINES"
    SCROLL_FAILED = "SCROLL_FAILED"
    SUCCESS = "SUCCESS"

class ScrollParams(BaseModel):
    direction: Optional[str] = Field(
        "down",
        description="The direction to scroll: 'up' or 'down'.",
        enum=["up", "down"]
    )
    lines: Optional[int] = Field(
        100,
        description="Number of lines to scroll by. Must be between 1 and 1000.",
        ge=1,
        le=1000
    )
    scroll_id: Optional[int] = Field(
        0,
        description="Unique ID for each scroll request. Increment this ID for consecutive scrolls."
    )

class ScrollResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result of the scroll action.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")