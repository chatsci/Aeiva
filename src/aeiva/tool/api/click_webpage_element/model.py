# model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ClickWebpageElementErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_SELECTOR_TYPE = "INVALID_SELECTOR_TYPE"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    SCROLL_FAILED = "SCROLL_FAILED"
    ELEMENT_NOT_INTERACTABLE = "ELEMENT_NOT_INTERACTABLE"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class ClickWebpageElementParams(BaseModel):
    url: str = Field(..., description="The URL of the webpage to interact with.")
    selector_type: str = Field(
        ..., 
        description="Type of selector to use (e.g., 'css', 'xpath', 'id', 'name', 'tag', 'class')."
    )
    selector: str = Field(..., description="The selector value to locate the element on the webpage.")
    timeout: Optional[float] = Field(10, description="Maximum time to wait for the element to be present (in seconds).")


class ClickWebpageElementResult(BaseModel):
    success: bool = Field(False, description="Whether the click action was successful")
    element_found: bool = Field(False, description="Whether the element was found on the page")
    scrolled_into_view: bool = Field(False, description="Whether the element was scrolled into view before clicking")
