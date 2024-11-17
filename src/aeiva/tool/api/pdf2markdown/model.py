# toolkit/file_toolkit/extract_file_as_markdown/model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Pdf2MarkdownErrorCode:
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    IO_ERROR = "IO_ERROR"
    JS_EXECUTION_ERROR = "JS_EXECUTION_ERROR"
    UNSUPPORTED_OS = "UNSUPPORTED_OS"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class Pdf2MarkdownParams(BaseModel):
    input_file_path: str = Field(..., description="The path to the input PDF file.")
    pages: Optional[List[int]] = Field(
        default=None,
        description="A list of 0-based page numbers to extract. If not provided, all pages are extracted."
    )
    output_file_path: Optional[str] = Field(
        default=None,
        description="The path to save the output Markdown file. If not provided, the Markdown text is returned."
    )


class Pdf2MarkdownResult(BaseModel):
    output: Optional[Dict[str, Any]] = Field(None, description="Result of the extraction.")
    error: Optional[str] = Field(None, description="Error message, if any.")
    error_code: str = Field(..., description="Error code representing the result state.")