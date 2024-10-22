import os
import json
import asyncio
from typing import Any, Callable
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

    def load_tool_schema(self, api_name: str) -> dict:
        """
        Load the tool's schema from the JSON file.
        Args:
            api_name (str): The name of the API or function.
        Returns:
            dict: The loaded schema from the JSON file.
        """
        current_path = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_path, "../../../.."))
        path = os.path.join(
            project_root,
            f"src/aeiva/action/tool/api/function/{api_name}/{api_name}.json",
        )
        with open(path, "r") as file:
            return json.load(file)

    async def execute(self, params: dict) -> Any:
        """
        Execute the tool by calling the corresponding function (whether it's for a local function or encapsulated API call).
        Args:
            params (dict): Parameters to pass to the tool.
        Returns:
            Any: The result of the tool execution.
        """
        function_module = f"aeiva.action.tool.api.function.{self.api_name}.api"
        func = __import__(function_module, fromlist=[self.api_name])

        # Check if the function is async
        function: Callable = getattr(func, self.api_name)
        if asyncio.iscoroutinefunction(function):
            return await function(**params)
        else:
            return function(**params)