import asyncio

def percept_terminal_input(prompt_message: str = "Please enter input: "):
    while True:
        user_input = input(prompt_message)
        if user_input is not None:
            if user_input.lower() in ["exit", "quit"]:  # Allow exiting the loop
                break
        yield user_input  # Yield the input instead of returning