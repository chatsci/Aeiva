# toolkit/system_toolkit/list_processes/model.py

from enum import Enum
from pydantic import BaseModel, Field

class ListProcessesParams(BaseModel):
    # No parameters needed for this API
    pass

class ListProcessesResult(BaseModel):
    output: dict = Field(
        ..., 
        description="List of currently running processes."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class ListProcessesErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"