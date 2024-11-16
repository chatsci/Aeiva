# toolkit/system_toolkit/kill_process/model.py

from enum import Enum
from pydantic import BaseModel, Field

class KillProcessParams(BaseModel):
    process_identifier: str = Field(
        ..., 
        description="The PID (as string) or name of the process to terminate."
    )

class KillProcessResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the process was terminated."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class KillProcessErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    PROCESS_NOT_FOUND = "PROCESS_NOT_FOUND"
    TERMINATION_TIMEOUT = "TERMINATION_TIMEOUT"
    FAILED_TO_TERMINATE = "FAILED_TO_TERMINATE"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"