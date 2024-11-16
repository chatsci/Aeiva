# toolkit/system_toolkit/get_package_root/model.py

from enum import Enum
from pydantic import BaseModel, Field

class GetPackageRootParams(BaseModel):
    package_name: str = Field(
        ...,
        description="The name of the package to find the root directory for."
    )

class GetPackageRootResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Output containing the package root directory."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class GetPackageRootErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    PACKAGE_NOT_FOUND = "PACKAGE_NOT_FOUND"
    IMPORT_ERROR = "IMPORT_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"