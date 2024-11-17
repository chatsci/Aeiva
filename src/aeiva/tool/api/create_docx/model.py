from pydantic import BaseModel, Field
from typing import Any, Dict

class CreateDocxErrorCode:
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class CreateDocxParams(BaseModel):
    output_file_path: str = Field(..., description="The path to save the new DOCX file.")

class CreateDocxResult(BaseModel):
    result: Dict[str, Any] = Field(..., description="Result of the DOCX creation.")
    error: str = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")