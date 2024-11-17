from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class Docx2ImagesErrorCode:
    SUCCESS = "SUCCESS"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class Docx2ImagesParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input DOCX file.")
    output_file_path: Optional[str] = Field(None, description="The directory to save extracted images.")

class Docx2ImagesResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Result of the image extraction.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")