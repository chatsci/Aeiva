# toolkit/file_toolkit/change_permissions/model.py

from enum import Enum
from pydantic import BaseModel, Field

class ChangePermissionsParams(BaseModel):
    path: str = Field(
        ..., 
        description="The path of the file or folder."
    )
    mode: int = Field(
        ..., 
        description="The new permission mode (e.g., 0o755)."
    )

class ChangePermissionsResult(BaseModel):
    output: str = Field(
        ..., 
        description="Success message indicating the permissions were changed."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class ChangePermissionsErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FAILED_TO_CHANGE_PERMISSIONS = "FAILED_TO_CHANGE_PERMISSIONS"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"