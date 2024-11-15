# tools/read_file/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ReadFileErrorCode:
    MISSING_FILE_PATH = "MISSING_FILE_PATH"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    READ_FILE_FAILED = "READ_FILE_FAILED"
    SUCCESS = "SUCCESS"

class ReadFileParams(BaseModel):
    file_path: str = Field(..., description="The path to the file.", sanitize=True)

class ReadFileResult(BaseModel):
    output: Optional[str] = Field(None, description="The content of the file.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")