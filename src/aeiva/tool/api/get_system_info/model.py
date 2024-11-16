# toolkit/system_toolkit/get_system_info/model.py

from enum import Enum
from pydantic import BaseModel, Field

class GetSystemInfoParams(BaseModel):
    # No parameters needed for this API
    pass

class GetSystemInfoResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Comprehensive system information."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class GetSystemInfoErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"