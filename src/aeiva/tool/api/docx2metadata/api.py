from typing import Any, Dict
from docx import Document


def docx2metadata(input_file_path: str) -> Dict[str, Any]:
    """
    Extracts metadata from a DOCX file.

    Args:
        input_file_path (str): The path to the input DOCX file.

    Returns:
        Dict[str, Any]: A dictionary containing 'result', 'error', and 'error_code'.
                        On success, 'result' includes the metadata.
    """
    try:
        document = Document(input_file_path)
        core_properties = document.core_properties
        metadata = {
            "author": core_properties.author,
            "title": core_properties.title,
            "subject": core_properties.subject,
            "keywords": core_properties.keywords,
            "last_modified_by": core_properties.last_modified_by,
            "created": core_properties.created,
            "modified": core_properties.modified
        }
        return {
            "result": {"metadata": metadata},
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "result": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }