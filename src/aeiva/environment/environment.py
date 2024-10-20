from abc import ABC, abstractmethod
from typing import Any
import asyncio


class Environment(ABC):
    """
    Abstract base class representing an environment in which agents can operate.
    
    The environment is responsible for managing its own state and providing mechanisms
    to observe, interact with, and update its state. It is independent of the agents
    that interact with it, focusing solely on its own dynamics and properties.

    Attributes:
        config (Any): Configuration settings for the environment.
        state (Any): The internal state of the environment.
    """

    def __init__(self, config: Any):
        """
        Initialize the environment with the provided configuration.

        Args:
            config (Any): Configuration settings for the environment.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal state of the environment.

        This method should set up the initial state required for the environment's operations.

        Returns:
            Any: The initial state of the environment.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """
        Asynchronously set up the environment's components.

        This method should initialize any necessary components or resources based on the provided configuration.

        Raises:
            EnvironmentSetupError: If the setup process fails.
        """
        pass

    @abstractmethod
    async def reset(self) -> None:
        """
        Asynchronously reset the environment to its initial state.

        This method resets the environment state, preparing it for a new interaction cycle.
        """
        pass

    @abstractmethod
    async def update(self, external_input: Any) -> None:
        """
        Asynchronously update the environment based on external inputs.

        Args:
            external_input (Any): External input (e.g., natural events or user-defined inputs) that affects the environment's state.

        Raises:
            EnvironmentUpdateError: If updating the environment fails.
        """
        pass

    @abstractmethod
    def get_observation(self) -> Any:
        """
        Retrieve the current observation of the environment.

        This method allows querying the environment's state, which could be in the form
        of sensor data, visual data, or other structured observations.

        Returns:
            Any: The current observation of the environment.
        """
        pass

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during environment operations.

        Args:
            error (Exception): The exception that was raised.
        """
        print(f"Environment encountered an error: {error}")
