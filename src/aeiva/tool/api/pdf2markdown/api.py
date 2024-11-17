# toolkit/file_toolkit/extract_file_as_markdown/api.py

from typing import Any, Dict, Optional, List
import pymupdf4llm  # Ensure this package is installed
import os


def pdf2markdown(
    input_file_path: str,
    pages: Optional[List[int]] = None,
    output_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts content from a PDF file and converts it to Markdown format.
    Optionally, specific pages can be selected, and the output can be saved to a file.

    Args:
        input_file_path (str): The path to the input PDF file.
        pages (List[int], optional): A list of 0-based page numbers to extract. Defaults to None, which extracts all pages.
        output_file_path (str, optional): The path to save the output Markdown file. If not provided, the Markdown text is returned.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
                        On success, 'output' includes the 'markdown' content or a success message if saved to a file.
    """
    try:
        # Check if the input file exists
        if not os.path.isfile(input_file_path):
            return {
                "output": None,
                "error": f"Input file '{input_file_path}' does not exist.",
                "error_code": "FILE_NOT_FOUND"
            }

        # Convert PDF to Markdown
        try:
            markdown_text = pymupdf4llm.to_markdown(input_file_path, pages)
        except Exception as e:
            return {
                "output": None,
                "error": f"JS_EXECUTION_ERROR: {e}",
                "error_code": "JS_EXECUTION_ERROR"
            }

        if output_file_path:
            # Save the Markdown text to the specified file
            try:
                with open(output_file_path, 'w', encoding='utf-8') as md_file:
                    md_file.write(markdown_text)
                return {
                    "output": {"message": f"Markdown file saved to '{output_file_path}'."},
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
            # Return the Markdown text
            return {
                "output": {"markdown": markdown_text},
                "error": None,
                "error_code": "SUCCESS"
            }

    except Exception as e:
        return {
            "output": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }