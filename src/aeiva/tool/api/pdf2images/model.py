# toolkit/file_toolkit/pdf2images/model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Pdf2ImagesErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    IO_ERROR = "IO_ERROR"
    IMAGE_EXTRACTION_ERROR = "IMAGE_EXTRACTION_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class Pdf2ImagesParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input PDF file.")
    pages: Optional[List[int]] = Field(
        default=None,
        description="A list of 0-based page numbers to extract images from. If not provided, images from all pages are extracted."
    )
    output_format: Optional[str] = Field(
        default="png",
        description="The format to save the extracted images. Supported formats: 'png', 'jpeg'. Defaults to 'png'."
    )
    output_directory: Optional[str] = Field(
        default=None,
        description="The directory to save the extracted images. If not provided, images are returned in the response."
    )


class Pdf2ImagesResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Result of the image extraction.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")