from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CloseBrowserTabErrorCode:
    SUCCESS = "SUCCESS"
    CLOSE_TAB_FAILED = "CLOSE_TAB_FAILED"

class CloseBrowserTabParams(BaseModel):
    page_id: int = Field(..., description="Page index to close.")

class CloseBrowserTabResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'closed_page_id': <int>}")
    error: Optional[str] = Field(None, description="Any error message.")
    error_code: str = Field(..., description="SUCCESS or failure code.")