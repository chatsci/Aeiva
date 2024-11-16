# toolkit/system_toolkit/clean_temp_files/api.py

import os
import shutil
from typing import Dict, Any

def clean_temp_files(paths: list = None) -> Dict[str, Any]:
    """
    Removes temporary files to free up space.

    Args:
        paths (list, optional): List of directories to clean. Defaults to system temp directories.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if paths is None:
            import tempfile
            paths = [tempfile.gettempdir()]
        
        cleaned_paths = []
        failed_paths = {}

        for path in paths:
            if not os.path.exists(path):
                failed_paths[path] = "Path does not exist."
                continue
            if not os.path.isdir(path):
                failed_paths[path] = "Path is not a directory."
                continue
            try:
                for filename in os.listdir(path):
                    file_path = os.path.join(path, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        cleaned_paths.append(file_path)
                    except Exception as e:
                        failed_paths[file_path] = str(e)
            except Exception as e:
                failed_paths[path] = str(e)
        
        return {
            "output": {
                "cleaned_files": cleaned_paths,
                "failed_files": failed_paths
            },
            "error": None if not failed_paths else "Some files/directories could not be deleted.",
            "error_code": "SUCCESS" if not failed_paths else "PARTIAL_SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to clean temporary files: {str(e)}",
            "error_code": "FAILED_TO_CLEAN_TEMP_FILES"
        }