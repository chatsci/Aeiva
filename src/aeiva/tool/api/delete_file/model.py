# src/aeiva/api/function/delete_file/models.py

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class DeleteFileErrorCode(str, Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    DELETE_FAILED = "DELETE_FAILED"
    SUCCESS = "SUCCESS"

class DeleteFileParams(BaseModel):
    file_path: str = Field(..., description="The path to the file.", sanitize=True)
    confirm: bool = Field(False, description="Confirmation flag to proceed with deletion.")

class DeleteFileResult(BaseModel):
    output: Optional[str] = Field(None, description="Success message.")
    error: Optional[str] = Field(None, description="Error message.")
    error_code: Optional[DeleteFileErrorCode] = Field(None, description="Error code.")