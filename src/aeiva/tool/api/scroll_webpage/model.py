from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ScrollWebpageErrorCode:
    SUCCESS = "SUCCESS"
    SCROLL_FAILED = "SCROLL_FAILED"

class ScrollWebpageParams(BaseModel):
    page_id: int = Field(..., description="Page index to scroll.")
    x: int = Field(0, description="Horizontal scroll offset.")
    y: int = Field(1000, description="Vertical scroll offset.")

class ScrollWebpageResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'scroll_x':..., 'scroll_y':...}")
    error: Optional[str] = Field(None, description="If any error.")
    error_code: str = Field(..., description="SUCCESS or error code.")