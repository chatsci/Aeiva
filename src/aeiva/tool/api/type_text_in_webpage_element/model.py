# type_text_in_webpage_element/model.py

from typing import Optional

from pydantic import BaseModel, Field


class TypeTextInWebpageElementParams(BaseModel):
    """Parameters for typing text into a webpage element."""

    selector: str = Field(
        ...,
        description="Selector value of the element to interact with.",
    )
    text: str = Field(
        ...,
        description="Text to type into the element.",
    )
    selector_type: str = Field(
        default="css",
        description="Type of selector to use (e.g., 'css', 'xpath', 'id', 'name', 'tag', 'class').",
    )
    clear_existing: bool = Field(
        default=False,
        description="Whether to clear existing text before typing.",
    )


class TypeTextInWebpageElementResult(BaseModel):
    """Result of the type_text_in_webpage_element action."""

    output: dict = Field(
        ..., description="Result data of the typing action."
    )
    error: Optional[str] = Field(
        None, description="Error message if the action failed."
    )
    error_code: str = Field(
        ..., description="Error code indicating the type of error."
    )


class TypeTextInWebpageElementErrorCode:
    """Error codes for the type_text_in_webpage_element action."""

    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_SELECTOR_TYPE = "INVALID_SELECTOR_TYPE"
    MISSING_SELECTOR = "MISSING_SELECTOR"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_NOT_INTERACTABLE = "ELEMENT_NOT_INTERACTABLE"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"