# aeiva/tool/api/browser_go_back/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class BrowserGoBackErrorCode:
    SUCCESS = "SUCCESS"
    BROWSER_GO_BACK_FAILED = "BROWSER_GO_BACK_FAILED"

class BrowserGoBackParams(BaseModel):
    page_id: int = Field(..., description="Index of the page in context.pages.")

class BrowserGoBackResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id': <int>}")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: str = Field(..., description="Indicates success or failure.")