from typing import Any, Dict
from docx import Document

def create_docx(output_file_path: str) -> Dict[str, Any]:
    """
    Creates a new DOCX file.

    Args:
        output_file_path (str): The path to save the new DOCX file.

    Returns:
        Dict[str, Any]: A dictionary containing 'result', 'error', and 'error_code'.
                        On success, 'result' includes a success message.
    """
    try:
        document = Document()
        document.save(output_file_path)
        return {
            "result": {"message": f"DOCX file created at '{output_file_path}'."},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "result": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }