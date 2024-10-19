# File: cognition/action_system.py

from abc import ABC, abstractmethod
from typing import Any


class ActionSystem(ABC):
    """
    Abstract base class representing the Action System of an agent.

    The Action System is responsible for executing actions within the environment based on
    directives from other cognitive components.

    Attributes:
        config (Any): Configuration settings for the Action System.
        state (Any): The internal state of the Action System, including the current action.
    """

    def __init__(self, config: Any):
        """
        Initialize the Action System with the provided configuration.

        Args:
            config (Any): Configuration settings for the Action System.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal state of the Action System.

        This method should set up the initial state required for the Action System's operations.

        Returns:
            Any: The initial state of the Action System.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """
        Asynchronously set up the Action System's components.

        This method should initialize any necessary components or resources based on the provided configuration.

        Raises:
            ConfigurationError: If the configuration is invalid or incomplete.
        """
        pass

    @abstractmethod
    async def execute(self, action: Any) -> None:
        """
        Asynchronously execute the specified action within the environment.

        Args:
            action (Any): The action to be executed.

        Raises:
            ExecutionError: If executing the action fails.
        """
        pass

    def get_current_action(self) -> Any:
        """
        Retrieve the current action being executed by the Action System.

        Returns:
            Any: The current action.
        """
        return self.state.get("current_action", None)

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during action operations.

        This method can be overridden to implement custom error handling logic, such as logging
        or retry mechanisms.

        Args:
            error (Exception): The exception that was raised.
        """
        # Default error handling: log the error
        print(f"ActionSystem encountered an error: {error}")