# tools/close_application/api.py

import psutil

def close_application(process_name: str) -> str:
    """
    Close an application gracefully.

    Args:
        process_name (str): The name of the process to terminate.

    Returns:
        str: A message indicating the result.
    """
    try:
        found = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == process_name:
                proc.terminate()
                found = True
        if found:
            return f"Application '{process_name}' terminated."
        else:
            return f"No running application found with name '{process_name}'."
    except Exception as e:
        return f"Error closing application: {e}"