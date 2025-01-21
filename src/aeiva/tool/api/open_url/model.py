# aeiva/tool/api/open_url/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class OpenUrlErrorCode:
    SUCCESS = "SUCCESS"
    OPEN_URL_FAILED = "OPEN_URL_FAILED"
    URL_NOT_PROVIDED = "URL_NOT_PROVIDED"

class OpenUrlParams(BaseModel):
    url: str = Field(..., description="The URL to open in a new browser page.")

class OpenUrlResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="If success, {'page_id': int, 'opened_url': str}"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if any."
    )
    error_code: str = Field(
        ...,
        description="Error code: 'SUCCESS', 'OPEN_URL_FAILED', or 'URL_NOT_PROVIDED'."
    )