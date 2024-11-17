from typing import Any, Dict
from docx2pdf import convert


def docx2pdf(input_file_path: str, output_file_path: str) -> Dict[str, Any]:
    """
    Converts a DOCX file to PDF format.

    Args:
        input_file_path (str): The path to the input DOCX file.
        output_file_path (str): The path to save the output PDF file.

    Returns:
        Dict[str, Any]: A dictionary containing 'result', 'error', and 'error_code'.
                        On success, 'result' includes a success message.
    """
    try:
        convert(input_file_path, output_file_path)
        return {
            "result": {"message": f"DOCX file converted to PDF at '{output_file_path}'."},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "result": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }