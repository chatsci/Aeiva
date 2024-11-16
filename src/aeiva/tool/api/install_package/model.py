# toolkit/system_toolkit/install_package/model.py

from enum import Enum
from pydantic import BaseModel, Field

class InstallPackageParams(BaseModel):
    package_name: str = Field(
        ..., 
        description="The name of the package to install."
    )
    package_type: str = Field(
        "python",
        description="Type of package ('python' or 'system'). Defaults to 'python'."
    )

class InstallPackageResult(BaseModel):
    output: str = Field(
        ..., 
        description="Output from the package installation command."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class InstallPackageErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_INSTALL_PACKAGE = "FAILED_TO_INSTALL_PACKAGE"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNSUPPORTED_DISTRIBUTION = "UNSUPPORTED_DISTRIBUTION"
    UNSUPPORTED_PACKAGE_TYPE = "UNSUPPORTED_PACKAGE_TYPE"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"