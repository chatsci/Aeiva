from pydantic import BaseModel, Field
from typing import Any, Dict

class Docx2MetadataErrorCode:
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class Docx2MetadataParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input DOCX file.")

class Docx2MetadataResult(BaseModel):
    result: Dict[str, Any] = Field(..., description="Result of the metadata extraction.")
    error: str = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")