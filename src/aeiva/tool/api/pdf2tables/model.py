# toolkit/file_toolkit/pdf2tables/model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Pdf2TablesErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    IO_ERROR = "IO_ERROR"
    TABLE_EXTRACTION_ERROR = "TABLE_EXTRACTION_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class Pdf2TablesParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input PDF file.")
    pages: Optional[List[int]] = Field(
        default=None,
        description="A list of 0-based page numbers to extract tables from. If not provided, tables from all pages are extracted."
    )
    output_format: Optional[str] = Field(
        default="json",
        description="The format to save the extracted tables. Supported formats: 'json', 'csv'. Defaults to 'json'."
    )
    output_file_path: Optional[str] = Field(
        default=None,
        description="The path to save the extracted tables. If not provided, the tables are returned in the response."
    )


class Pdf2TablesResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Result of the table extraction.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")