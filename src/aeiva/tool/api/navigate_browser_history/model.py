# navigate_browser_history/model.py

from pydantic import BaseModel, Field, Optional


class NavigateBrowserHistoryParams(BaseModel):
    """Parameters for navigating browser history."""

    direction: str = Field(
        ...,
        description="Direction to navigate: 'back' or 'forward'.",
    )
    steps: int = Field(
        default=1,
        ge=1,
        description="Number of steps to navigate in the specified direction.",
    )


class NavigateBrowserHistoryResult(BaseModel):
    """Result of the navigate_browser_history action."""

    output: dict = Field(
        ..., description="Result data of the navigation history action."
    )
    error: Optional[str] = Field(
        None, description="Error message if the action failed."
    )
    error_code: str = Field(
        ..., description="Error code indicating the type of error."
    )


class NavigateBrowserHistoryErrorCode:
    """Error codes for the navigate_browser_history action."""

    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_DIRECTION = "INVALID_DIRECTION"
    INVALID_STEPS = "INVALID_STEPS"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"