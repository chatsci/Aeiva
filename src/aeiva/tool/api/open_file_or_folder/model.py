# tools/open_file_or_folder/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class OpenFileOrFolderErrorCode:
    MISSING_PATH = "MISSING_PATH"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    OPEN_FAILED = "OPEN_FAILED"
    SUCCESS = "SUCCESS"

class OpenFileOrFolderParams(BaseModel):
    path: str = Field(..., description="The path to the file or folder.", sanitize=True)

class OpenFileOrFolderResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")