# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class EditFileErrorCode:
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INVALID_LINE_RANGE = "INVALID_LINE_RANGE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    OS_ERROR = "OS_ERROR"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class EditFileParams(BaseModel):
    file_path: Optional[str] = Field(None, description="The path to the file that will be edited. If not provided, edits the currently open file.")
    text: str = Field(..., description="The text that will replace the specified line range in the file.")
    start_line: int = Field(..., description="The line number at which the file edit will start (inclusive).")
    end_line: Optional[int] = Field(None, description="The line number at which the file edit will end (inclusive). If not provided, appends the text.")

class EditFileResult(BaseModel):
    output: Optional[str] = Field(None, description="Message indicating the result of the edit action.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")