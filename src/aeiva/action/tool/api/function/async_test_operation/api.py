import asyncio

async def async_test_operation(a: int, b: int) -> dict:
    """
    Example asynchronous local tool function.
    Args:
        a (int): First input value.
        b (int): Second input value.
    Returns:
        dict: Result of the operation.
    """
    await asyncio.sleep(1)  # Simulate asynchronous operation (e.g., I/O-bound task)
    result = a + b
    return {"result": result}