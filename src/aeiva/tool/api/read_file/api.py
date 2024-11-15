# tools/read_file/api.py

from typing import Dict, Any
import os

def read_file(file_path: str) -> Dict[str, Any]:
    """
    Reads the contents of a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not file_path:
            return {
                "output": None,
                "error": "File path must be provided.",
                "error_code": "MISSING_FILE_PATH"
            }

        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            return {
                "output": None,
                "error": f"File not found: {file_path}",
                "error_code": "FILE_NOT_FOUND"
            }

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "output": content,
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error reading file: {e}",
            "error_code": "READ_FILE_FAILED"
        }