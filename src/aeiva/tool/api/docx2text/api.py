from typing import Any, Dict, Optional
from docx import Document


def docx2text(
    input_file_path: str,
    output_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts text from a DOCX file.

    Args:
        input_file_path (str): The path to the input DOCX file.
        output_file_path (str, optional): The path to save the extracted text file.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        doc = Document(input_file_path)
        full_text = []
        for paragraph in doc.paragraphs:
            full_text.append(paragraph.text)

        text_content = '\n'.join(full_text)

        if output_file_path:
            with open(output_file_path, 'w', encoding='utf-8') as text_file:
                text_file.write(text_content)
            return {
                "output": {
                    "message": f"Text content saved to '{output_file_path}'."
                },
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            return {
                "output": {
                    "text": text_content
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