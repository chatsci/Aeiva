# tools/open_application/api.py

import os
import subprocess
import sys

def open_application(application_path: str) -> str:
    """
    Launch an application.

    Args:
        application_path (str): The path to the application executable.

    Returns:
        str: A message indicating the result.
    """
    try:
        application_path = os.path.expanduser(application_path)

        if not os.path.exists(application_path):
            return f"Application not found: {application_path}"

        if sys.platform.startswith('win'):
            os.startfile(application_path)
        elif sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
            subprocess.Popen([application_path])
        else:
            return "Unsupported operating system."
        return f"Application opened: {application_path}"
    except Exception as e:
        return f"Error opening application: {e}"