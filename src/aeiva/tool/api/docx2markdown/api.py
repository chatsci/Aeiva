from typing import Any, Dict, Optional
from docx import Document
import markdownify


def docx2markdown(
    input_file_path: str,
    output_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Converts a DOCX file to Markdown format.

    Args:
        input_file_path (str): The path to the input DOCX file.
        output_file_path (str, optional): The path to save the converted Markdown file.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        doc = Document(input_file_path)
        md_content = markdownify.markdownify(doc)

        if output_file_path:
            with open(output_file_path, 'w', encoding='utf-8') as md_file:
                md_file.write(md_content)
            return {
                "output": {
                    "message": f"Markdown content saved to '{output_file_path}'."
                },
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            return {
                "output": {
                    "markdown": md_content
                },
                "error": None,
                "error_code": "SUCCESS"
            }

    except Exception as e:
        return {
            "output": None,
            "error": f"UNEXPECTED_ERROR: {e}",
            "error_code": "UNEXPECTED_ERROR"
        }