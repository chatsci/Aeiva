# toolkit/file_toolkit/pdf2text/api.py

from typing import Any, Dict, Optional, List
import os
import pypdf
import pdfplumber


def pdf2text(
    input_file_path: str,
    pages: Optional[List[int]] = None,
    output_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts text from a PDF file.
    Optionally, specific pages can be selected, and the text can be saved to a file.

    Args:
        input_file_path (str): The path to the input PDF file.
        pages (List[int], optional): A list of 0-based page numbers to extract text from.
                                     If None, all pages are extracted.
        output_file_path (str, optional): The path to save the extracted text file.
                                          If None, the text content is returned.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
                        On success, 'output' includes the 'text' content or a success message if saved to a file.
    """
    try:
        # Check if the input file exists
        if not os.path.isfile(input_file_path):
            return {
                "output": None,
                "error": f"Input file '{input_file_path}' does not exist.",
                "error_code": "FILE_NOT_FOUND"
            }

        # Initialize text accumulator
        extracted_text = ""

        # Using pdfplumber for better text extraction with layout preservation
        try:
            with pdfplumber.open(input_file_path) as pdf:
                total_pages = len(pdf.pages)
                if pages:
                    selected_pages = [p for p in pages if 0 <= p < total_pages]
                else:
                    selected_pages = list(range(total_pages))

                for page_number in selected_pages:
                    page = pdf.pages[page_number]
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
        except Exception as e:
            return {
                "output": None,
                "error": f"IO_ERROR: {e}",
                "error_code": "IO_ERROR"
            }

        if output_file_path:
            # Save the extracted text to the specified file
            try:
                with open(output_file_path, 'w', encoding='utf-8') as text_file:
                    text_file.write(extracted_text)
                return {
                    "output": {"message": f"Text extracted and saved to '{output_file_path}'."},
                    "error": None,
                    "error_code": "SUCCESS"
                }
            except IOError as io_err:
                return {
                    "output": None,
                    "error": f"IO_ERROR: {io_err}",
                    "error_code": "IO_ERROR"
                }
        else:
            # Return the extracted text
            return {
                "output": {"text": extracted_text},
                "error": None,
                "error_code": "SUCCESS"
            }

    except Exception as e:
        return {
            "output": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }