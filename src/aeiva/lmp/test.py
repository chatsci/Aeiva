# test.py

from aeiva.lmp.lmp import simple, complex, llm_client
import json
from aeiva.tool.tool import Tool

def main():
    # test @simple decorator
    @simple(model='gpt-4', temperature=0.7)
    def greet(name: str):
        """You are a helpful assistant."""
        return f"Say hello to {name}!"

    response = greet("Alice")
    print("\n=== Simple Decorator Response ===")
    print(response)

    # test @complex decorator
    tools=["test_operation"]
    tools=[Tool.load_tool_schema(tool) for tool in tools]  # get the list of json dicts for all function tools.

    @complex(model='gpt-4', tools=tools)
    def tool_bot():
        """You are a calculator."""
        return [
            {'role': 'system', 'content': "You are a calculator."},
            {'role': 'user', 'content': "How much is 3 test operation 4?"}
        ]

    response = tool_bot()
    print("\n=== Complex Decorator Response ===")
    print(response)

if __name__ == "__main__":
    main()