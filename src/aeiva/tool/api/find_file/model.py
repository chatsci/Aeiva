# tools/find_file/model.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class FindFileErrorCode:
    MISSING_PATTERN = "MISSING_PATTERN"
    NO_MATCHES = "NO_MATCHES"
    TOO_MANY_RESULTS = "TOO_MANY_RESULTS"
    FIND_FILE_FAILED = "FIND_FILE_FAILED"
    SUCCESS = "SUCCESS"

class FindFileParams(BaseModel):
    pattern: str = Field(..., description="Pattern to search for (supports wildcards, e.g., \"*.txt\").")
    depth: Optional[int] = Field(None, description="Maximum depth to search. None for unlimited.", ge=0)
    case_sensitive: Optional[bool] = Field(False, description="If true, the search is case-sensitive.")
    include: Optional[List[str]] = Field(None, description="List of directories to include in the search.")
    exclude: Optional[List[str]] = Field(None, description="List of directories to exclude from the search.")

class FindFileResult(BaseModel):
    output: Optional[List[str]] = Field(None, description="List of file paths matching the search pattern.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")