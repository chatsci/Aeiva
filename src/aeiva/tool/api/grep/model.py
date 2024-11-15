# model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Tuple

class GrepErrorCode:
    MISSING_WORD = "MISSING_WORD"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    NO_MATCHES = "NO_MATCHES"
    TOO_MANY_MATCHES = "TOO_MANY_MATCHES"
    NO_FILES_FOUND = "NO_FILES_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    IO_ERROR = "IO_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    SUCCESS = "SUCCESS"

class GrepParams(BaseModel):
    word: str = Field(..., description="The term to search for.")
    pattern: Optional[str] = Field(None, description="The file, directory, or glob pattern to search in. If not provided, searches in the current working directory.")
    recursive: Optional[bool] = Field(True, description="If true, search recursively in subdirectories.")
    case_insensitive: Optional[bool] = Field(True, description="If true, perform case-insensitive search.")

class GrepResult(BaseModel):
    output: Optional[Dict[str, List[Tuple[int, str]]]] = Field(None, description="A dictionary with file paths as keys and lists of (line number, line content) tuples as values.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")