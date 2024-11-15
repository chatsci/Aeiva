# src/aeiva/api/function/delete_file/api.py

import os
from typing import Dict, Any

async def delete_file(file_path: str, confirm: bool = False) -> Dict[str, Any]:
    """
    Deletes a specified file after confirmation.

    Args:
        file_path (str): The path to the file.
        confirm (bool): Confirmation flag to proceed with deletion.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    if not os.path.isfile(file_path):
        return {
            "output": "",
            "error": f"File not found: {file_path}",
            "error_code": "FILE_NOT_FOUND"
        }

    if not confirm:
        return {
            "output": "",
            "error": "Deletion not confirmed.",
            "error_code": "CONFIRMATION_REQUIRED"
        }

    try:
        os.remove(file_path)
        return {
            "output": f"File deleted successfully: {file_path}",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": "",
            "error": str(e),
            "error_code": "DELETE_FAILED"
        }