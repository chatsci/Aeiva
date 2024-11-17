# toolkit/file_toolkit/pdf2ocr/model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Pdf2OcrErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    OCR_ERROR = "OCR_ERROR"
    IO_ERROR = "IO_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class Pdf2OcrParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input PDF file.")
    output_file_path: Optional[str] = Field(
        default=None,
        description="The path to save the OCR-processed PDF file. If not provided, the OCR text is returned."
    )
    language: Optional[str] = Field(
        default="eng",
        description="The language to use for OCR. Defaults to 'eng' (English)."
    )


class Pdf2OcrResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Result of the OCR process.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")