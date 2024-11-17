from typing import Any, Dict, Optional
from docx import Document
import os


def docx2images(
    input_file_path: str,
    output_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts images from a DOCX file and saves them to a specified directory.

    Args:
        input_file_path (str): The path to the input DOCX file.
        output_file_path (str, optional): The directory to save extracted images.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not os.path.isfile(input_file_path):
            return {
                "output": None,
                "error": f"Input file '{input_file_path}' does not exist.",
                "error_code": "FILE_NOT_FOUND"
            }

        doc = Document(input_file_path)
        image_count = 0
        if output_file_path:
            os.makedirs(output_file_path, exist_ok=True)

        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                image_count += 1
                img_data = rel.target_part.blob
                img_name = f"image_{image_count}.png"
                img_path = os.path.join(output_file_path, img_name)
                with open(img_path, "wb") as img_file:
                    img_file.write(img_data)

        return {
            "output": {
                "message": f"{image_count} images extracted."
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