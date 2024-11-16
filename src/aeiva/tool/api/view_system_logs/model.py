# toolkit/system_toolkit/view_system_logs/model.py

from enum import Enum
from pydantic import BaseModel, Field

class ViewSystemLogsParams(BaseModel):
    log_type: str = Field(
        "system",
        description="Type of logs to retrieve ('system' or 'application'). Defaults to 'system'."
    )

class ViewSystemLogsResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Retrieved system logs."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class ViewSystemLogsErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_VIEW_LOGS = "FAILED_TO_VIEW_LOGS"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNSUPPORTED_LOG_TYPE = "UNSUPPORTED_LOG_TYPE"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"