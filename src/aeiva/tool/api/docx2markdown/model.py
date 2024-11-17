from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

class Docx2MarkdownErrorCode:
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class Docx2MarkdownParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input DOCX file.")
    output_file_path: Optional[str] = Field(None, description="The path to save the converted Markdown file.")

class Docx2MarkdownResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Result of the Markdown conversion.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")