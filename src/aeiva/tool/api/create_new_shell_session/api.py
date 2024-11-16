# toolkit/shell_toolkit/create_new_shell_session/api.py

import subprocess
import platform
import uuid
from typing import Dict, Any
from threading import Lock

# Global registry to keep track of shell sessions
# In a production environment, consider more robust session management
shell_sessions = {}
session_lock = Lock()

def create_new_shell_session(session_name: str = None, shell_type: str = None) -> Dict[str, Any]:
    """
    Initializes a new shell session for executing commands in an isolated environment.

    Args:
        session_name (str, optional): A custom name for the shell session.
        shell_type (str, optional): The type of shell to use (e.g., 'bash', 'zsh', 'powershell', 'cmd'). 
                                    Defaults to the system's default shell.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
                        On success, 'output' includes the 'session_id'.
    """
    try:
        system = platform.system()
        
        if not shell_type:
            if system in ["Linux", "Darwin"]:  # Unix-like systems
                shell_type = "/bin/bash"
            elif system == "Windows":
                shell_type = "powershell"
            else:
                return {
                    "output": None,
                    "error": f"Unsupported operating system: {system}",
                    "error_code": "UNSUPPORTED_OS"
                }
        else:
            # Validate shell_type based on OS
            if system in ["Linux", "Darwin"] and shell_type not in ["/bin/bash", "/bin/zsh"]:
                return {
                    "output": None,
                    "error": f"Unsupported shell type '{shell_type}' for {system}.",
                    "error_code": "UNSUPPORTED_SHELL_TYPE"
                }
            elif system == "Windows" and shell_type.lower() not in ["powershell", "cmd"]:
                return {
                    "output": None,
                    "error": f"Unsupported shell type '{shell_type}' for Windows.",
                    "error_code": "UNSUPPORTED_SHELL_TYPE"
                }
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        if not session_name:
            session_name = f"shell_session_{session_id}"
        
        # Start the shell process
        if system in ["Linux", "Darwin"]:
            process = subprocess.Popen([shell_type], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elif system == "Windows":
            if shell_type.lower() == "powershell":
                process = subprocess.Popen([shell_type, "-NoExit"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            elif shell_type.lower() == "cmd":
                process = subprocess.Popen([shell_type], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            return {
                "output": None,
                "error": f"Unsupported operating system: {system}",
                "error_code": "UNSUPPORTED_OS"
            }
        
        # Register the session
        with session_lock:
            shell_sessions[session_id] = {
                "name": session_name,
                "process": process,
                "shell_type": shell_type
            }
        
        return {
            "output": {"session_id": session_id, "session_name": session_name},
            "error": None,
            "error_code": "SUCCESS"
        }
    
    except FileNotFoundError:
        return {
            "output": None,
            "error": f"Shell '{shell_type}' not found on the system.",
            "error_code": "SHELL_NOT_FOUND"
        }
    except PermissionError:
        return {
            "output": None,
            "error": f"Permission denied while trying to start shell '{shell_type}'.",
            "error_code": "PERMISSION_DENIED"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to create new shell session: {str(e)}",
            "error_code": "FAILED_TO_CREATE_SESSION"
        }