# scroll_webpage/model.py

from typing import Optional

from pydantic import BaseModel, Field


class ScrollWebpageParams(BaseModel):
    """Parameters for scrolling the webpage."""

    selector: Optional[str] = Field(
        default=None,
        description="Selector value of the element to interact with.",
    )
    selector_type: str = Field(
        default="css",
        description="Type of selector to use (e.g., 'css', 'xpath', 'id', 'name', 'tag', 'class').",
    )
    scroll_type: str = Field(
        default="pixels",
        description="Type of scroll action: 'pixels' or 'element'.",
    )
    direction: str = Field(
        default="down",
        description="Direction to scroll: 'up', 'down', 'left', or 'right'.",
    )
    amount: Optional[int] = Field(
        default=200,
        description="Number of pixels to scroll (required for 'pixels' scroll type).",
    )


class ScrollWebpageResult(BaseModel):
    """Result of the scroll_webpage action."""

    output: dict = Field(
        ..., description="Result data of the scroll action."
    )
    error: Optional[str] = Field(
        None, description="Error message if the action failed."
    )
    error_code: str = Field(
        ..., description="Error code indicating the type of error."
    )


class ScrollWebpageErrorCode:
    """Error codes for the scroll_webpage action."""

    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_SCROLL_TYPE = "INVALID_SCROLL_TYPE"
    INVALID_DIRECTION = "INVALID_DIRECTION"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    INVALID_SELECTOR_TYPE = "INVALID_SELECTOR_TYPE"
    MISSING_SELECTOR = "MISSING_SELECTOR"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"