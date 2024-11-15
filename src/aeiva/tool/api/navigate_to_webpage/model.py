# navigate_to_webpage/model.py

from pydantic import BaseModel, Field, Optional


class NavigateToWebpageParams(BaseModel):
    """Parameters for navigating to a webpage."""

    url: str = Field(
        ...,
        description="Full URL of the webpage to navigate to, including the protocol (e.g., 'https://www.example.com').",
    )
    timeout: int = Field(
        default=30000,
        description="Maximum time to wait for navigation to complete (in milliseconds).",
    )


class NavigateToWebpageResult(BaseModel):
    """Result of the navigate_to_webpage action."""

    output: dict = Field(
        ..., description="Result data of the navigation action."
    )
    error: Optional[str] = Field(
        None, description="Error message if the action failed."
    )
    error_code: str = Field(
        ..., description="Error code indicating the type of error."
    )


class NavigateToWebpageErrorCode:
    """Error codes for the navigate_to_webpage action."""

    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"