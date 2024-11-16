# toolkit/system_toolkit/get_env_var/model.py

from enum import Enum
from pydantic import BaseModel, Field

class GetEnvVarParams(BaseModel):
    var_name: str = Field(
        ..., 
        description="The name of the environment variable to retrieve."
    )

class GetEnvVarResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Value of the specified environment variable."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class GetEnvVarErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    ENV_VAR_NOT_FOUND = "ENV_VAR_NOT_FOUND"
    FAILED_TO_GET_ENV_VAR = "FAILED_TO_GET_ENV_VAR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"