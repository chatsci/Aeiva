# api/api_tools/hello_world/api.py

def greet(name: str = "world"):
    """Greet a user by name."""
    return f"Hello, {name}!"