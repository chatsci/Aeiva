# toolkit/system_toolkit/monitor_system_resources/model.py

from enum import Enum
from pydantic import BaseModel, Field

class MonitorSystemResourcesParams(BaseModel):
    interval: float = Field(
        1.0,
        description="Time in seconds between each resource check."
    )

class MonitorSystemResourcesResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Current system resource usage."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class MonitorSystemResourcesErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_MONITOR_RESOURCES = "FAILED_TO_MONITOR_RESOURCES"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"