import subprocess
from typing import Dict, Optional, Any


def execute_bash_command(command: str, session_id: Optional[str] = None, restart: bool = False) -> Dict[str, Any]:
    """
    Execute a bash command in a persistent or new session.

    Args:
        command (str): Bash command to be executed.
        session_id (Optional[str]): ID of the bash session. If None, executes in a new shell.
        restart (bool): Whether to restart the session before executing the command.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    if not command.strip():
        return {
            "output": None,
            "error": "Command cannot be empty.",
            "error_code": "INVALID_COMMAND",
        }

    try:
        if restart or session_id is None:
            # Restarting the session or creating a new one
            session = subprocess.Popen(
                ["bash"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            session_id = session.pid
        else:
            # Use an existing session (mock implementation)
            # In real-world scenarios, this would attach to a persistent session
            session = subprocess.Popen(
                ["bash"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        stdout, stderr = session.communicate(command)
        exit_code = session.returncode

        return {
            "output": {
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
                "exit_code": exit_code,
                "session_id": session_id,
            },
            "error": None,
            "error_code": "SUCCESS",
        }
    except subprocess.SubprocessError as e:
        return {
            "output": None,
            "error": f"Execution failed: {str(e)}",
            "error_code": "EXECUTION_FAILED",
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"An unexpected error occurred: {str(e)}",
            "error_code": "UNKNOWN_ERROR",
        }