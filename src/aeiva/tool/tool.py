import os
import json
import asyncio
from typing import Any, Callable
from importlib import import_module
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Tool:
    def __init__(self, api_name: str):
        """
        Initialize the tool, determining whether it should run locally or via an external service.
        Args:
            api_name (str): The name of the tool API (matches the function name).
        """
        self.api_name = api_name
        self.schema = self.load_tool_schema(api_name)

    @classmethod
    def load_tool_schema(cls, api_name: str) -> dict:
        """
        Load the tool's schema from the JSON file.
        Args:
            api_name (str): The name of the API or function.
        Returns:
            dict: The loaded schema from the JSON file.
        """
        current_path = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_path, "../../.."))
        path = os.path.join(
            project_root,
            f"src/aeiva/tool/api/{api_name}/{api_name}.json",
        )
        with open(path, "r") as file:
            return json.load(file)

    async def aexecute(self, params: dict) -> Any:
        """
        Execute the tool by calling the corresponding function (whether it's for a local function or encapsulated API call).
        Args:
            params (dict): Parameters to pass to the tool.
        Returns:
            Any: The result of the tool execution.
        """
        function_module = f"aeiva.tool.api.{self.api_name}.api"
        func_module = import_module(function_module)

        # Check if the function is async
        function: Callable = getattr(func_module, self.api_name)
        if asyncio.iscoroutinefunction(function):
            return await function(**params)
        else:
            return function(**params)

    def execute(self, params: dict) -> Any:
        """
        Execute the tool synchronously by calling the corresponding function.

        Args:
            params (dict): Parameters to pass to the tool.

        Returns:
            Any: The result of the tool execution.
        """
        function_module = f"aeiva.tool.api.{self.api_name}.api"
        func_module = import_module(function_module)

        function: Callable = getattr(func_module, self.api_name)
        if asyncio.iscoroutinefunction(function):
            # If the function is async, attempt to run it in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If an event loop is running, create a task and wait for it
                task = loop.create_task(function(**params))
                return loop.run_until_complete(task)
            except RuntimeError:
                # No event loop running, use asyncio.run
                return asyncio.run(function(**params))
        else:
            # If the function is synchronous, call it directly
            return function(**params)