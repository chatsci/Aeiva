# tools/web_search/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class WebSearchErrorCode:
    MISSING_QUERY = "MISSING_QUERY"
    SEARCH_FAILED = "SEARCH_FAILED"
    WEB_SEARCH_FAILED = "WEB_SEARCH_FAILED"
    SUCCESS = "SUCCESS"

class WebSearchParams(BaseModel):
    query: str = Field(..., description="The search query string.")

class WebSearchResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="The search results.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")