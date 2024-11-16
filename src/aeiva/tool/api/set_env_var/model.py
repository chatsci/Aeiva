# toolkit/system_toolkit/set_env_var/model.py

from enum import Enum
from pydantic import BaseModel, Field

class SetEnvVarParams(BaseModel):
    var_name: str = Field(
        ..., 
        description="The name of the environment variable to set."
    )
    value: str = Field(
        ..., 
        description="The value to set for the environment variable."
    )

class SetEnvVarResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the environment variable was set."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class SetEnvVarErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_SET_ENV_VAR = "FAILED_TO_SET_ENV_VAR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"