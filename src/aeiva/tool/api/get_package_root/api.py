# toolkit/system_toolkit/get_package_root/api.py

import importlib
import os
import sys
from typing import Dict, Any

def get_package_root(package_name: str) -> Dict[str, Any]:
    """
    Obtain the root directory of a given package.

    Args:
        package_name (str): The name of the package.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        spec = importlib.util.find_spec(package_name)
        if spec is None or spec.origin is None:
            return {
                "output": None,
                "error": f"Cannot find package '{package_name}'.",
                "error_code": "PACKAGE_NOT_FOUND",
            }
        package_path = os.path.dirname(os.path.abspath(spec.origin))
        return {
            "output": {"package_root": package_path},
            "error": None,
            "error_code": "SUCCESS",
        }
    except ImportError as e:
        return {
            "output": None,
            "error": f"ImportError: {str(e)}",
            "error_code": "IMPORT_ERROR",
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"An unexpected error occurred: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
        }