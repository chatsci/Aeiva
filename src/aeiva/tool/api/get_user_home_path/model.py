# toolkit/system_toolkit/get_user_home_path/model.py

from enum import Enum
from pydantic import BaseModel, Field

class GetUserHomePathParams(BaseModel):
    # No parameters needed for this API
    pass

class GetUserHomePathResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Output containing the user's home directory path."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class GetUserHomePathErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    INVALID_HOME_DIRECTORY = "INVALID_HOME_DIRECTORY"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"