# tools/open_application/model.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class OpenApplicationErrorCode:
    MISSING_APPLICATION_PATH = "MISSING_APPLICATION_PATH"
    APPLICATION_NOT_FOUND = "APPLICATION_NOT_FOUND"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    OPEN_APPLICATION_FAILED = "OPEN_APPLICATION_FAILED"
    SUCCESS = "SUCCESS"

class OpenApplicationParams(BaseModel):
    application_path: str = Field(..., description="The path to the application executable.")

class OpenApplicationResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")