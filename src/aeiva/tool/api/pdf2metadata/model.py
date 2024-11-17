# toolkit/file_toolkit/pdf2metadata/model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Pdf2MetadataErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    IO_ERROR = "IO_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class Pdf2MetadataParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input PDF file.")


class Pdf2MetadataResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Metadata extracted from the PDF.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")