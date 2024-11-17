# toolkit/file_toolkit/pdf2ocr/api.py

from typing import Any, Dict, Optional, List
import os
import ocrmypdf
from pypdf import PdfReader


def pdf2ocr(
    input_file_path: str,
    output_file_path: Optional[str] = None,
    language: Optional[str] = "eng"
) -> Dict[str, Any]:
    """
    Performs OCR on a PDF file to make it searchable.
    Optionally, the OCR-processed PDF can be saved to a specified path.

    Args:
        input_file_path (str): The path to the input PDF file.
        output_file_path (str, optional): The path to save the OCR-processed PDF file.
                                          If not provided, the OCR text is returned.
        language (str, optional): The language to use for OCR. Defaults to 'eng' (English).

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
                        On success, 'output' includes the OCR text or a success message if saved to a file.
    """
    try:
        # Validate language parameter
        if not isinstance(language, str) or not language:
            return {
                "output": None,
                "error": "Invalid language parameter. It must be a non-empty string.",
                "error_code": "VALIDATION_ERROR"
            }

        # Check if the input file exists
        if not os.path.isfile(input_file_path):
            return {
                "output": None,
                "error": f"Input file '{input_file_path}' does not exist.",
                "error_code": "FILE_NOT_FOUND"
            }

        if output_file_path:
            # Perform OCR and save the output PDF
            try:
                ocrmypdf.ocr(input_file_path, output_file_path, language=language, force_ocr=True)
                return {
                    "output": {"message": f"OCR completed and saved to '{output_file_path}'."},
                    "error": None,
                    "error_code": "SUCCESS"
                }
            except ocrmypdf.exceptions.OCRError as ocr_err:
                return {
                    "output": None,
                    "error": f"OCR_ERROR: {ocr_err}",
                    "error_code": "OCR_ERROR"
                }
            except IOError as io_err:
                return {
                    "output": None,
                    "error": f"IO_ERROR: {io_err}",
                    "error_code": "IO_ERROR"
                }
        else:
            # Perform OCR and return the text content
            try:
                # Perform OCR and save to a temporary file
                temp_output = "temp_ocr.pdf"
                ocrmypdf.ocr(input_file_path, temp_output, language=language, force_ocr=True)

                # Extract text from the OCRed PDF using PyPDF
                reader = PdfReader(temp_output)
                extracted_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"

                # Remove the temporary file
                os.remove(temp_output)

                return {
                    "output": {"text": extracted_text},
                    "error": None,
                    "error_code": "SUCCESS"
                }
            except ocrmypdf.exceptions.OCRError as ocr_err:
                return {
                    "output": None,
                    "error": f"OCR_ERROR: {ocr_err}",
                    "error_code": "OCR_ERROR"
                }
            except IOError as io_err:
                return {
                    "output": None,
                    "error": f"IO_ERROR: {io_err}",
                    "error_code": "IO_ERROR"
                }
            except Exception as e:
                return {
                    "output": None,
                    "error": f"UNEXPECTED_ERROR: {e}",
                    "error_code": "UNEXPECTED_ERROR"
                }

    except Exception as e:
        return {
            "output": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }