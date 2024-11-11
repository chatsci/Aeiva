# tools/type_keyboard/api.py

import pyautogui

def type_keyboard(text: str, interval: float = 0.05) -> str:
    """
    Simulate keyboard typing to input text.

    Args:
        text (str): The text to type.
        interval (float): Time interval between each character.

    Returns:
        str: A message indicating the result.
    """
    try:
        pyautogui.write(text, interval=interval)
        return f"Typed text: '{text}'"
    except Exception as e:
        return f"Error typing text: {e}"