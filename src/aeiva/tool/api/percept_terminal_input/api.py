# import asyncio

# def percept_terminal_input(prompt_message: str = "Please enter input: "):
#     while True:
#         user_input = input(prompt_message)
#         if user_input is not None:
#             if user_input.lower() in ["exit", "quit"]:  # Allow exiting the loop
#                 break
#         yield user_input  # Yield the input instead of returning

# tools/percept_terminal_input/api.py

from typing import Dict, Any

def percept_terminal_input(prompt_message: str = "Please enter input: ") -> Dict[str, Any]:
    """
    Retrieves input from the terminal based on the provided prompt message.

    Args:
        prompt_message (str, optional): The prompt message to display to the user. Defaults to "Please enter input: ".

    Returns:
        Dict[str, Any]: A dictionary containing 'output', 'error', and 'error_code'.
    """
    try:
        user_input = input(prompt_message)
        if user_input.lower() in ["exit", "quit"]:
            return {
                "output": None,
                "error": "Input session terminated by user.",
                "error_code": "SESSION_TERMINATED"
            }
        return {
            "output": user_input,
            "error": None,
            "error_code": "SUCCESS"
        }
    except Exception as e:
        return {
            "output": None,
            "error": f"Error retrieving terminal input: {e}",
            "error_code": "INPUT_FAILED"
        }