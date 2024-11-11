# tools/click_on_element/api.py

import pyautogui

def click_on_element(position: dict) -> str:
    """
    Click on a GUI element at a specified position.

    Args:
        position (dict): The position dictionary containing 'x', 'y', 'width', 'height'.

    Returns:
        str: A message indicating the result.
    """
    try:
        x = position['x'] + position['width'] / 2
        y = position['y'] + position['height'] / 2
        pyautogui.click(x, y)
        return f"Clicked on element at ({x}, {y})."
    except Exception as e:
        return f"Error clicking on element: {e}"