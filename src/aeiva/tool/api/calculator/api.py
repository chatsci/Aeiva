from typing import Any, Dict


def calculator(operation: str) -> Dict[str, Any]:
    """
    Perform mathematical calculations based on the given operation.

    Args:
        operation (str): A mathematical expression, e.g., `200*7` or `5000/2*10`.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        if not operation.strip():
            return {
                "output": None,
                "error": "Operation cannot be empty.",
                "error_code": "INVALID_OPERATION",
            }

        # Perform the calculation safely
        result = eval(operation)  # Avoid eval in production without sanitization

        return {
            "output": {"result": str(result)},
            "error": None,
            "error_code": "SUCCESS",
        }
    except SyntaxError:
        return {
            "output": None,
            "error": "Invalid mathematical expression.",
            "error_code": "SYNTAX_ERROR",
        }
    except ZeroDivisionError:
        return {
            "output": None,
            "error": "Division by zero is not allowed.",
            "error_code": "DIVISION_BY_ZERO",
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
        }