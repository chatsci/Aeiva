# toolkit/system_toolkit/clean_temp_files/model.py

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class CleanTempFilesParams(BaseModel):
    paths: Optional[List[str]] = Field(
        None, 
        description="List of directories to clean. Defaults to system temp directories."
    )

class CleanTempFilesResult(BaseModel):
    output: dict = Field(
        ..., 
        description="Details of cleaned and failed files/directories."
    )
    error: str = Field(
        None, 
        description="Error message, if any."
    )
    error_code: str = Field(
        ..., 
        description="Error code representing the result state."
    )

class CleanTempFilesErrorCode(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED_TO_CLEAN_TEMP_FILES = "FAILED_TO_CLEAN_TEMP_FILES"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"