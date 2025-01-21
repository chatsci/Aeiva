from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class BrowserGoForwardErrorCode:
    SUCCESS = "SUCCESS"
    BROWSER_GO_FORWARD_FAILED = "BROWSER_GO_FORWARD_FAILED"

class BrowserGoForwardParams(BaseModel):
    page_id: int = Field(..., description="Index of the page.")

class BrowserGoForwardResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id': <int>}")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: str = Field(..., description="Indicates success or failure.")