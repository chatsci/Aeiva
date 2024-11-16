# toolkit/file_toolkit/get_file_metadata/api.py

import os
import platform
from typing import Dict, Any
import subprocess

def get_file_metadata(path: str) -> Dict[str, Any]:
    """
    Retrieves metadata information about a file or folder.

    Args:
        path (str): The path of the file or folder.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not os.path.exists(path):
            return {
                "output": None,
                "error": f"Path '{path}' does not exist.",
                "error_code": "PATH_NOT_FOUND"
            }
        
        system = platform.system()
        metadata = {}
        
        if system in ["Linux", "Darwin"]:  # Unix-like systems
            stat_info = os.stat(path)
            metadata = {
                "mode": oct(stat_info.st_mode),
                "size": stat_info.st_size,
                "last_modified": stat_info.st_mtime,
                "last_accessed": stat_info.st_atime,
                "created": stat_info.st_ctime
            }
        elif system == "Windows":
            # Using PowerShell to get file metadata
            command = ["powershell", "-Command", f"Get-Item '{path}' | Select-Object Mode, Length, LastWriteTime, LastAccessTime, CreationTime | ConvertTo-Json"]
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            metadata = result.stdout
        else:
            return {
                "output": None,
                "error": f"Unsupported operating system: {system}",
                "error_code": "UNSUPPORTED_OS"
            }
        
        return {
            "output": {"metadata": metadata},
            "error": None,
            "error_code": "SUCCESS"
        }
    except subprocess.CalledProcessError as e:
        return {
            "output": None,
            "error": f"Failed to retrieve metadata for '{path}': {e.stderr.strip()}",
            "error_code": "FAILED_TO_GET_METADATA"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to retrieve metadata for '{path}': {str(e)}",
            "error_code": "FAILED_TO_GET_METADATA"
        }