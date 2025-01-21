from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SwitchBrowserTabErrorCode:
    SUCCESS = "SUCCESS"
    INVALID_PAGE_ID = "INVALID_PAGE_ID"
    SWITCH_TAB_FAILED = "SWITCH_TAB_FAILED"

class SwitchBrowserTabParams(BaseModel):
    page_id: int = Field(..., description="Page index to switch to.")

class SwitchBrowserTabResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'switched_page_id': ...}")
    error: Optional[str] = Field(None, description="If any error.")
    error_code: str = Field(..., description="SUCCESS or error code.")