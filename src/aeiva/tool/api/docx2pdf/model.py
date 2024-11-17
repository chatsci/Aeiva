from pydantic import BaseModel, Field
from typing import Any, Dict

class Docx2PdfErrorCode:
    SUCCESS = "SUCCESS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

class Docx2PdfParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input DOCX file.")
    output_file_path: str = Field(..., description="The path to save the output PDF file.")

class Docx2PdfResult(BaseModel):
    result: Dict[str, Any] = Field(..., description="Result of the PDF conversion.")
    error: str = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")