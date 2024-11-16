# toolkit/system_toolkit/create_user/model.py

from enum import Enum
from pydantic import BaseModel, Field

class CreateUserParams(BaseModel):
    username: str = Field(
        ..., 
        description="The username for the new user."
    )
    password: str = Field(
        ..., 
        description="The password for the new user."
    )

class CreateUserResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the user was created."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class CreateUserErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_CREATE_USER = "FAILED_TO_CREATE_USER"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"