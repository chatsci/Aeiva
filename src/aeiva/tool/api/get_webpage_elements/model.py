# model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class GetWebpageElementsErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_SELECTOR_TYPE = "INVALID_SELECTOR_TYPE"
    NO_ELEMENTS_FOUND = "NO_ELEMENTS_FOUND"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class GetWebpageElementsParams(BaseModel):
    url: str = Field(..., description="The URL of the webpage to interact with.")
    selector_type: str = Field(
        ..., 
        description="Type of selector to use (e.g., 'css', 'xpath', 'id', 'name', 'tag', 'class')."
    )
    selector: str = Field(..., description="The selector value to locate elements on the webpage.")
    timeout: Optional[float] = Field(10, description="Maximum time to wait for elements to be present (in seconds).")


class GetWebpageElementsResult(BaseModel):
    elements: List[Dict[str, Any]] = Field(default_factory=list, description="List of elements with their details")
