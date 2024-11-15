# tools/list_files/model.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ListFilesErrorCode:
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
    LIST_FILES_FAILED = "LIST_FILES_FAILED"
    SUCCESS = "SUCCESS"

class ListFilesParams(BaseModel):
    directory: Optional[str] = Field(None, description="The directory to list files from.")

class ListFilesResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="List of files and directories.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")