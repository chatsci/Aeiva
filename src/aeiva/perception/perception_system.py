# File: cognition/perception_system.py

from abc import ABC, abstractmethod
from typing import Any


class PerceptionSystem(ABC):
    """
    Abstract base class representing the Perception System of an agent.

    The Perception System is responsible for capturing raw sensory data from the environment,
    processing this data into meaningful observations, and providing access to these observations
    for other components of the cognitive architecture.

    Attributes:
        config (Any): Configuration settings for the Perception System.
        state (Any): The internal state of the Perception System, including raw data and observations.
    """

    def __init__(self, config: Any):
        """
        Initialize the Perception System with the provided configuration.

        Args:
            config (Any): Configuration settings for the Perception System.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal state of the Perception System.

        This method should set up the initial state required for the Perception System's operations.

        Returns:
            Any: The initial state of the Perception System.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """
        Asynchronously set up the Perception System's components.

        This method should initialize any necessary components or resources based on the provided configuration.

        Raises:
            ConfigurationError: If the configuration is invalid or incomplete.
        """
        pass

    @abstractmethod
    async def capture(self, raw_data: Any) -> None:
        """
        Asynchronously capture raw sensory data from the environment.

        Args:
            raw_data (Any): The raw sensory data to capture.

        Raises:
            CaptureError: If capturing the raw data fails.
        """
        pass

    @abstractmethod
    async def process(self) -> None:
        """
        Asynchronously process the captured raw sensory data into meaningful observations.

        This method should transform raw data stored in the internal state into structured observations
        that can be utilized by other components of the cognitive architecture.

        Raises:
            ProcessingError: If processing the raw data fails.
        """
        pass

    async def perceive(self, raw_data: Any) -> None:
        """
        Asynchronously perform the full perception cycle: capture and process raw sensory data.

        Args:
            raw_data (Any): The raw sensory data to perceive.

        Raises:
            CaptureError: If capturing the raw data fails.
            ProcessingError: If processing the raw data fails.
        """
        try:
            await self.capture(raw_data)
            await self.process()
        except Exception as e:
            self.handle_error(e)
            raise e

    def get_observations(self) -> Any:
        """
        Retrieve the current processed observations from the Perception System.

        Returns:
            Any: The current observations.
        """
        return self.state.get("observations", None)

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during perception operations.

        This method can be overridden to implement custom error handling logic, such as logging
        or retry mechanisms.

        Args:
            error (Exception): The exception that was raised.
        """
        # Default error handling: log the error
        print(f"PerceptionSystem encountered an error: {error}")
