# toolkit/system_toolkit/set_env_var/api.py

import os
from typing import Dict, Any

def set_env_var(var_name: str, value: str) -> Dict[str, Any]:
    """
    Sets or updates the value of a specified environment variable.

    Args:
        var_name (str): The name of the environment variable.
        value (str): The value to set for the environment variable.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        os.environ[var_name] = value
        return {
            "output": f"Environment variable '{var_name}' set to '{value}'.",
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to set environment variable '{var_name}': {str(e)}",
            "error_code": "FAILED_TO_SET_ENV_VAR"
        }