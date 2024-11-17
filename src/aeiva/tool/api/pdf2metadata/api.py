# toolkit/file_toolkit/pdf2metadata/api.py

from typing import Any, Dict, Optional, List
import os
from pypdf import PdfReader


def pdf2metadata(
    input_file_path: str
) -> Dict[str, Any]:
    """
    Extracts metadata from a PDF file.

    Args:
        input_file_path (str): The path to the input PDF file.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
                        On success, 'output' includes the extracted metadata.
    """
    try:
        # Check if the input file exists
        if not os.path.isfile(input_file_path):
            return {
                "output": None,
                "error": f"Input file '{input_file_path}' does not exist.",
                "error_code": "FILE_NOT_FOUND"
            }

        # Extract metadata using PyPDF
        try:
            reader = PdfReader(input_file_path)
            metadata = reader.metadata  # Returns a dictionary-like object
            # Convert to regular dictionary and remove leading '/'
            cleaned_metadata = {key.strip('/'): value for key, value in metadata.items()}
        except Exception as e:
            return {
                "output": None,
                "error": f"IO_ERROR: {e}",
                "error_code": "IO_ERROR"
            }

        # Return the metadata
        return {
            "output": {"metadata": cleaned_metadata},
            "error": None,
            "error_code": "SUCCESS"
        }

    except Exception as e:
        return {
            "output": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }