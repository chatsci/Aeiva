# tools/write_file/api.py

from typing import Dict, Any
import os

def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes content to a file.

    Args:
        file_path (str): The path to the file.
        content (str): The content to write into the file.

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
        directory = os.path.dirname(file_path)

        # Ensure the directory exists and is writable
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                return {
                    "output": None,
                    "error": f"Error creating directory: {e}",
                    "error_code": "CREATE_DIRECTORY_FAILED"
                }

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "output": f"Content written to {file_path}",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error writing to file: {e}",
            "error_code": "WRITE_FILE_FAILED"
        }