# toolkit/system_toolkit/get_env_var/api.py

import os
from typing import Dict, Any

def get_env_var(var_name: str) -> Dict[str, Any]:
    """
    Retrieves the value of a specified environment variable.

    Args:
        var_name (str): The name of the environment variable.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        value = os.environ.get(var_name)
        if value is not None:
            return {
                "output": {"value": value},
                "error": None,
                "error_code": "SUCCESS"
            }
        else:
            return {
                "output": None,
                "error": f"Environment variable '{var_name}' not found.",
                "error_code": "ENV_VAR_NOT_FOUND"
            }
    except Exception as e:
        return {
            "output": None,
            "error": f"Failed to get environment variable '{var_name}': {str(e)}",
            "error_code": "FAILED_TO_GET_ENV_VAR"
        }