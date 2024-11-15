# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class RenameFileErrorCode:
    MISSING_PATHS = "MISSING_PATHS"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    DESTINATION_EXISTS = "DESTINATION_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    OS_ERROR = "OS_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class RenameFileParams(BaseModel):
    old_file_path: str = Field(..., description="Old file path to rename. This is a relative or absolute path to the file.")
    new_file_path: str = Field(..., description="New file path to rename to. This is a relative or absolute path to the file.")

class RenameFileResult(BaseModel):
    output: Optional[str] = Field(None, description="Message indicating the result of the rename action.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")