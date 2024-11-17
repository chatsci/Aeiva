from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class ModifyDocxErrorCode:
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class ModifyDocxParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input DOCX file.")
    modifications: Dict[str, Any] = Field(..., description="The modifications to apply.")
    output_file_path: Optional[str] = Field(None, description="The path to save the modified DOCX file.")

class ModifyDocxResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Result of the document modification.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")