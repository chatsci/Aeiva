from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ExtractWebpageContentErrorCode:
    SUCCESS = "SUCCESS"
    EXTRACT_CONTENT_FAILED = "EXTRACT_CONTENT_FAILED"

class ExtractWebpageContentParams(BaseModel):
    page_id: int = Field(..., description="Page index.")
    format: str = Field("text", description="One of ['text', 'html'].")

class ExtractWebpageContentResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'format': ..., 'content': ...}")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: str = Field(..., description="SUCCESS or error type.")