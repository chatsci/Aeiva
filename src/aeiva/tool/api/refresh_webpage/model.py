# refresh_webpage/model.py

from pydantic import BaseModel, Field
from typing import Optional


class RefreshWebpageParams(BaseModel):
    """Parameters for refreshing the current webpage."""

    ignore_cache: bool = Field(
        default=False,
        description="If True, the browser cache will be ignored when refreshing the page.",
    )


class RefreshWebpageResult(BaseModel):
    """Result of the refresh_webpage action."""

    output: dict = Field(
        ..., description="Result data of the refresh action."
    )
    error: Optional[str] = Field(
        None, description="Error message if the action failed."
    )
    error_code: str = Field(
        ..., description="Error code indicating the type of error."
    )


class RefreshWebpageErrorCode:
    """Error codes for the refresh_webpage action."""

    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    WEBDRIVER_ERROR = "WEBDRIVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"