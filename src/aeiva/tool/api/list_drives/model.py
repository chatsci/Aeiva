# toolkit/system_toolkit/list_drives/model.py

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict

class ListDrivesParams(BaseModel):
    # No parameters needed for this API
    pass

class ListDrivesResult(BaseModel):
    output: dict = Field(
        ..., 
        description="List of mounted drives or partitions."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class ListDrivesErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_LIST_DRIVES = "FAILED_TO_LIST_DRIVES"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"