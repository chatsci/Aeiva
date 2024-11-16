# toolkit/system_toolkit/get_user_home_path/api.py

import os
import platform
from pathlib import Path
from typing import Dict, Any

def get_user_home_path() -> Dict[str, Any]:
    """
    Retrieves the home directory of the current user across different platforms.

    Supported Platforms:
        - Windows
        - macOS
        - Linux
        - iOS (best-effort)
        - Android (best-effort)

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        system = platform.system()
        print(f"Detected operating system: {system}")  # Replace with logger if needed

        if system == "Windows":
            # Windows: Use USERPROFILE or combine HOMEDRIVE and HOMEPATH
            home = os.environ.get('USERPROFILE') or os.path.join(os.environ.get('HOMEDRIVE', ''), os.environ.get('HOMEPATH', ''))
            print(f"Windows home directory: {home}")  # Replace with logger if needed
        elif system in ["Linux", "Darwin"]:  # Darwin is macOS
            # Unix-like systems: Use expanduser
            home = os.path.expanduser("~")
            print(f"Unix-like home directory: {home}")  # Replace with logger if needed
        elif system == "Java":  # Potentially Android (e.g., running via Jython or similar)
            # Android typically uses /data/user/0/<package_name>/ or /sdcard/
            # However, accessing these paths may require specific permissions
            # Here, we attempt to use the HOME environment variable
            home = os.environ.get('HOME') or '/sdcard/'
            print(f"Android home directory (best-effort): {home}")  # Replace with logger if needed
        elif system == "iOS":
            # iOS applications are sandboxed; home directory is typically the app's sandbox
            # Accessing it might require specific APIs or configurations
            # Here, we return the current working directory as a placeholder
            home = Path.cwd()
            print(f"iOS home directory (best-effort): {home}")  # Replace with logger if needed
        else:
            # Fallback for unknown systems
            home = os.path.expanduser("~")
            print(f"Unknown system '{system}'. Falling back to expanduser: {home}")  # Replace with logger if needed

        if home and os.path.isdir(home):
            return {
                "output": {"user_home": str(Path(home).resolve())},
                "error": None,
                "error_code": "SUCCESS",
            }
        else:
            return {
                "output": None,
                "error": "Determined home directory does not exist or is not a directory.",
                "error_code": "INVALID_HOME_DIRECTORY",
            }
    
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to determine the user's home directory: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
        }