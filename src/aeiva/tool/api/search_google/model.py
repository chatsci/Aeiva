from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SearchGoogleErrorCode:
    SUCCESS = "SUCCESS"
    SEARCH_GOOGLE_FAILED = "SEARCH_GOOGLE_FAILED"

class SearchGoogleParams(BaseModel):
    page_id: int = Field(..., description="Index of the page.")
    query: str = Field(..., description="Search text to enter.")

class SearchGoogleResult(BaseModel):
    result: Optional[Dict[str, Any]] = Field(None, description="{'page_id':..., 'query':...}")
    error: Optional[str] = Field(None, description="Error if any.")
    error_code: str = Field(..., description="SUCCESS or failure code.")