# tools/write_file/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class WriteFileErrorCode:
    MISSING_FILE_PATH = "MISSING_FILE_PATH"
    CREATE_DIRECTORY_FAILED = "CREATE_DIRECTORY_FAILED"
    WRITE_FILE_FAILED = "WRITE_FILE_FAILED"
    SUCCESS = "SUCCESS"

class WriteFileParams(BaseModel):
    file_path: str = Field(..., description="The path to the file.", sanitize=True)
    content: str = Field(..., description="The content to write into the file.")

class WriteFileResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")