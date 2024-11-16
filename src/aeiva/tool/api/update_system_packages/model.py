# toolkit/system_toolkit/update_system_packages/model.py

from enum import Enum
from pydantic import BaseModel, Field

class UpdateSystemPackagesParams(BaseModel):
    # No parameters needed for this API
    pass

class UpdateSystemPackagesResult(BaseModel):
    output: str = Field(
        ..., 
        description="Output from the package update command."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class UpdateSystemPackagesErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_UPDATE_PACKAGES = "FAILED_TO_UPDATE_PACKAGES"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNSUPPORTED_DISTRIBUTION = "UNSUPPORTED_DISTRIBUTION"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"