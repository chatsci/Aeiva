# File: cognition/emotion.py

from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar, Generic
import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# Define custom exceptions
class ConfigurationError(Exception):
    """Exception raised for errors in the configuration."""
    pass

class UpdateError(Exception):
    """Exception raised for errors during emotion state updates."""
    pass

class RegulationError(Exception):
    """Exception raised for errors during emotion regulation."""
    pass

T = TypeVar('T')  # Type variable for the state

class Emotion(ABC, Generic[T]):
    """
    Abstract base class representing the Emotion system of an agent with generic state type.

    The Emotion system manages the agent's emotional states, allowing it to respond
    to various stimuli in an emotionally coherent manner.

    Attributes:
        config (Dict[str, Any]): Configuration settings for the Emotion system.
        state (T): The internal emotional state of the agent, defined by subclasses.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Emotion system with the provided configuration.

        Args:
            config (Dict[str, Any]): Configuration settings for the Emotion system.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> T:
        """
        Initialize the internal emotional state of the Emotion system.

        This method should set up the initial emotional state required for the
        Emotion system's operations.

        Returns:
            T: The initial emotional state of the agent.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """
        Asynchronously set up the Emotion system's components.

        This method should initialize any necessary components or resources
        based on the provided configuration.

        Raises:
            ConfigurationError: If the configuration is invalid or incomplete.
        """
        pass

    @abstractmethod
    async def update(self, input_data: Dict[str, Any]) -> None:
        """
        Asynchronously update the emotional state based on input data.

        Args:
            input_data (Dict[str, Any]): The data or stimuli that influence the emotional state.

        Raises:
            UpdateError: If updating the emotional state fails.
        """
        pass

    @abstractmethod
    def regulate(self, strategy: str) -> None:
        """
        Regulate the emotional state using a specified strategy.

        Args:
            strategy (str): The regulation strategy to apply (e.g., 'suppression', 'amplification').

        Raises:
            RegulationError: If the regulation strategy is invalid or fails.
        """
        pass

    @abstractmethod
    def express(self) -> str:
        """
        Generate a representation of the current emotional state.

        Returns:
            str: A string describing the current emotion (e.g., "I feel happy!").
        """
        pass

    @abstractmethod
    def serialize(self) -> str:
        """
        Serialize the current emotional state into a string format.

        Returns:
            str: Serialized emotional state.
        """
        pass

    @abstractmethod
    def deserialize(self, data: str) -> None:
        """
        Deserialize the emotional state from a string format.

        Args:
            data (str): Serialized emotional state.
        """
        pass

    def get_current_state(self) -> T:
        """
        Retrieve the current emotional state of the agent.

        Returns:
            T: The current emotional state.
        """
        return self.state

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during emotional processing.

        This method can be overridden to implement custom error handling logic.

        Args:
            error (Exception): The exception that was raised.
        """
        pass
        # logger.error(f"Emotion system encountered an error: {error}", exc_info=True)