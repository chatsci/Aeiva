# model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class GetWebpageDetailsErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class GetWebpageDetailsParams(BaseModel):
    url: str = Field(..., description="The URL of the webpage to interact with.")
    include_accessibility: Optional[bool] = Field(
        True, description="Whether to include an accessibility snapshot of the page."
    )


class GetWebpageDetailsResult(BaseModel):
    title: Optional[str] = Field(None, description="The title of the webpage.")
    url: Optional[str] = Field(None, description="The current URL of the webpage.")
    meta_tags: Optional[List[Dict[str, Any]]] = Field(None, description="List of meta tags on the page.")
    accessibility_snapshot: Optional[Any] = Field(None, description="Accessibility snapshot of the page.")

