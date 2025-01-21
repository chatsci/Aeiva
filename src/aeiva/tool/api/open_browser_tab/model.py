from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class OpenBrowserTabErrorCode:
    SUCCESS = "SUCCESS"
    OPEN_TAB_FAILED = "OPEN_TAB_FAILED"

class OpenBrowserTabParams(BaseModel):
    url: Optional[str] = Field(None, description="Optional URL to navigate.")

class OpenBrowserTabResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'opened_url':...}")
    error: Optional[str] = Field(None, description="If any error.")
    error_code: str = Field(..., description="SUCCESS or error type.")