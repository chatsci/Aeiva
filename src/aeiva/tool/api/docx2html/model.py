from pydantic import BaseModel, Field
from typing import Any, Dict

class Docx2HtmlErrorCode:
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class Docx2HtmlParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input DOCX file.")
    output_file_path: str = Field(..., description="The path to save the HTML content.")

class Docx2HtmlResult(BaseModel):
    result: Dict[str, Any] = Field(..., description="Result of the HTML conversion.")
    error: str = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")
