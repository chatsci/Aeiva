import sys
import reactivex as rx
from rxactivex import operators as ops

# Function to read input from the terminal
def user_input():
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        yield user_input  # Yield the input instead of returning

# Create an observable from the user input generator
input_stream = rx.from_iterable(user_input())

# Process the input and respond
input_stream.pipe(
    ops.map(lambda text: f"Response: {text}"),  # Transform input to response
).subscribe(
    on_next=lambda response: print(response),  # Print the response
    on_error=lambda e: print(f"Error: {e}"),
    on_completed=lambda: print("Input stream completed.")
)

# Run the program
print("Type your messages (type 'exit' or 'quit' to stop):")