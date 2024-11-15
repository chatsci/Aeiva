# tools/test_operation/api.py

from typing import Dict, Any

def test_operation(a: int, b: int) -> Dict[str, Any]:
    """
    Performs a test operation: a + b + a * b + 100.

    Args:
        a (int): The first operand.
        b (int): The second operand.

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        result = a + b + (a * b) + 100
        return {
            "output": result,
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error performing test operation: {e}",
            "error_code": "TEST_OPERATION_FAILED"
        }