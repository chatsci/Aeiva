# tools/type_into_element/api.py

import pyautogui

def type_into_element(position: dict, text: str) -> str:
    """
    Click on an input field and type text.

    Args:
        position (dict): The position dictionary containing 'x', 'y', 'width', 'height'.
        text (str): The text to type into the input field.

    Returns:
        str: A message indicating the result.
    """
    try:
        x = position['x'] + position['width'] / 2
        y = position['y'] + position['height'] / 2
        pyautogui.click(x, y)
        pyautogui.write(text, interval=0.05)
        return f"Typed into element at ({x}, {y})."
    except Exception as e:
        return f"Error typing into element: {e}"