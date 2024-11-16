# toolkit/system_toolkit/delete_user/model.py

from enum import Enum
from pydantic import BaseModel, Field

class DeleteUserParams(BaseModel):
    username: str = Field(
        ..., 
        description="The username of the user to remove."
    )

class DeleteUserResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the user was deleted."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class DeleteUserErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_DELETE_USER = "FAILED_TO_DELETE_USER"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"