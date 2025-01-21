from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ClickWebpageElementErrorCode:
    SUCCESS = "SUCCESS"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    CLICK_FAILED = "CLICK_FAILED"

class ClickWebpageElementParams(BaseModel):
    page_id: int = Field(..., description="Index of the page.")
    selector: str = Field(..., description="CSS selector for the element.")

class ClickWebpageElementResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'selector':...}")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: str = Field(..., description="Indicates success or failure.")