# toolkit/system_toolkit/get_disk_usage/model.py

from enum import Enum
from pydantic import BaseModel, Field

class GetDiskUsageParams(BaseModel):
    path: str = Field(
        "/",
        description="The path to check disk usage for."
    )

class GetDiskUsageResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Disk usage information."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class GetDiskUsageErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    FAILED_TO_GET_DISK_USAGE = "FAILED_TO_GET_DISK_USAGE"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"