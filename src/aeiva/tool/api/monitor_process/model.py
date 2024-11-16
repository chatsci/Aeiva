# toolkit/system_toolkit/monitor_process/model.py

from enum import Enum
from pydantic import BaseModel, Field

class MonitorProcessParams(BaseModel):
    process_identifier: str = Field(
        ..., 
        description="The PID (as string) or name of the process to monitor."
    )

class MonitorProcessResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Process information including status and resource usage."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class MonitorProcessErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    PROCESS_NOT_FOUND = "PROCESS_NOT_FOUND"
    FAILED_TO_MONITOR_PROCESS = "FAILED_TO_MONITOR_PROCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"