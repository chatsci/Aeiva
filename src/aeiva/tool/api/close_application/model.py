# tools/close_application/model.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CloseApplicationErrorCode:
    MISSING_PROCESS_NAME = "MISSING_PROCESS_NAME"
    PROCESS_NOT_FOUND = "PROCESS_NOT_FOUND"
    CLOSE_APPLICATION_FAILED = "CLOSE_APPLICATION_FAILED"
    SUCCESS = "SUCCESS"

class CloseApplicationParams(BaseModel):
    process_name: str = Field(..., description="The name of the process to terminate.")

class CloseApplicationResult(BaseModel):
    output: Optional[str] = Field(None, description="A message indicating the result.")
    error: Optional[str] = Field(None, description="Error message if any.")
    error_code: Optional[str] = Field(None, description="Error code indicating the result status.")