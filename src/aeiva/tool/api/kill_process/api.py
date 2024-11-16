# toolkit/system_toolkit/kill_process/api.py

import psutil
from typing import Dict, Any

def kill_process(process_identifier: str) -> Dict[str, Any]:
    """
    Terminates a specified process by PID or name.

    Args:
        process_identifier (str): The PID (as string) or name of the process to terminate.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if process_identifier.isdigit():
            pid = int(process_identifier)
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=5)
                return {
                    "output": f"Process with PID {pid} terminated successfully.",
                    "error": None,
                    "error_code": "SUCCESS"
                }
            except psutil.NoSuchProcess:
                return {
                    "output": None,
                    "error": f"No process found with PID {pid}.",
                    "error_code": "PROCESS_NOT_FOUND"
                }
            except psutil.TimeoutExpired:
                return {
                    "output": None,
                    "error": f"Process with PID {pid} did not terminate in time.",
                    "error_code": "TERMINATION_TIMEOUT"
                }
            except Exception as e:
                return {
                    "output": None,
                    "error": f"Failed to terminate process with PID {pid}: {str(e)}",
                    "error_code": "FAILED_TO_TERMINATE"
                }
        else:
            # Assume it's a process name
            found = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() == process_identifier.lower():
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                        found = True
                    except psutil.NoSuchProcess:
                        continue
                    except psutil.TimeoutExpired:
                        return {
                            "output": None,
                            "error": f"Process '{process_identifier}' did not terminate in time.",
                            "error_code": "TERMINATION_TIMEOUT"
                        }
                    except Exception as e:
                        return {
                            "output": None,
                            "error": f"Failed to terminate process '{process_identifier}': {str(e)}",
                            "error_code": "FAILED_TO_TERMINATE"
                        }
            if found:
                return {
                    "output": f"All instances of '{process_identifier}' terminated successfully.",
                    "error": None,
                    "error_code": "SUCCESS"
                }
            else:
                return {
                    "output": None,
                    "error": f"No process found with name '{process_identifier}'.",
                    "error_code": "PROCESS_NOT_FOUND"
                }
    except Exception as e:
        return {
            "output": None,
            "error": f"An unexpected error occurred: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }