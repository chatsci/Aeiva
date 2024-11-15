# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ChwdirErrorCode:
    EMPTY_PATH = "EMPTY_PATH"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    OS_ERROR = "OS_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class ChwdirParams(BaseModel):
    path: str = Field(..., description="The path to change the current working directory to. Can be absolute, relative, or use '..' to navigate up the directory tree.")

class ChwdirResult(BaseModel):
    output: Optional[str] = Field(None, description="Message indicating the new working directory.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")