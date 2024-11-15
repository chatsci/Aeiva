# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class CreateFileOrFolderErrorCode:
    EMPTY_PATH = "EMPTY_PATH"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    OS_ERROR = "OS_ERROR"
    DIRECTORY_EXISTS = "DIRECTORY_EXISTS"
    FILE_EXISTS = "FILE_EXISTS"
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class CreateFileOrFolderParams(BaseModel):
    path: str = Field(..., description="The path to create. If is_directory is false, creates a file. If is_directory is true, creates a directory.")
    is_directory: Optional[bool] = Field(False, description="Whether to create a directory instead of a file.")

class CreateFileOrFolderResult(BaseModel):
    output: Optional[str] = Field(None, description="Path of the created file or directory.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")