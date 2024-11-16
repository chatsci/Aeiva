# toolkit/system_toolkit/change_user_password/model.py

from enum import Enum
from pydantic import BaseModel, Field

class ChangeUserPasswordParams(BaseModel):
    username: str = Field(
        ..., 
        description="The username of the user."
    )
    new_password: str = Field(
        ..., 
        description="The new password to set."
    )

class ChangeUserPasswordResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the password was updated."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class ChangeUserPasswordErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_CHANGE_PASSWORD = "FAILED_TO_CHANGE_PASSWORD"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"