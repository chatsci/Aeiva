from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class NavigateToWebpageErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NAVIGATE_FAILED = "NAVIGATE_FAILED"

class NavigateToWebpageParams(BaseModel):
    page_id: int = Field(..., description="Which page to navigate.")
    url: str = Field(..., description="Destination URL.")

class NavigateToWebpageResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'url':...}")
    error: Optional[str] = Field(None, description="Any error message.")
    error_code: str = Field(..., description="SUCCESS or error type.")