# api/api_tools/test_operation/api.py

def test_operation(a: int, b: int) -> int:
    """
    Perform a test operation: a + b + a * b.

    Args:
        a (int): The first operand.
        b (int): The second operand.

    Returns:
        int: The result of a + b + a * b.
    """
    return a + b + (a * b) + 100