# File: cognition/brain.py

from abc import ABC, abstractmethod
from typing import Any


class Brain(ABC):
    """
    Abstract base class representing the cognitive processing unit.

    The Brain is responsible for processing input stimuli to generate cognitive states
    that the CognitionSystem will translate into actions.

    Attributes:
        config (Any): Configuration settings for the Brain.
        state (Any): The internal state of the Brain.
    """

    def __init__(self, config: Any):
        """
        Initialize the Brain with the provided configuration.

        Args:
            config (Any): Configuration settings for the Brain.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal state of the Brain.

        This method should set up the initial state required for the Brain's operations.

        Returns:
            Any: The initial state of the Brain.
        """
        pass

    @abstractmethod
    def setup(self) -> None:
        """
        Asynchronously set up the Brain's components.

        This method should initialize any necessary components or resources
        based on the provided configuration.

        Raises:
            ConfigurationError: If the configuration is invalid or incomplete.
        """
        pass

    @abstractmethod
    async def think(self, stimuli: Any, *args, **kwargs) -> Any:
        """
        Asynchronously process input stimuli to update the cognitive state.

        Args:
            stimuli (Any): The input stimuli to process.

        Returns:
            Any: The updated cognitive state.

        Raises:
            ProcessingError: If processing the stimuli fails.
        """
        pass

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during cognitive processing.

        This method can be overridden to implement custom error handling logic.

        Args:
            error (Exception): The exception that was raised.
        """
        # Default error handling: log the error
        print(f"Brain encountered an error: {error}")