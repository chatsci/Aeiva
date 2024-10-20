from abc import ABC, abstractmethod
from typing import Any, List

class SocialSystem(ABC):
    """
    Abstract base class representing a social system within the Society model.

    Each social system (e.g., communication, finance, governance) should inherit from this class
    and implement the necessary functionalities to manage specific aspects of the society.
    
    Attributes:
        config (Any): Configuration settings for the social system.
        state (Any): The internal state of the social system.
    """

    def __init__(self, config: Any):
        """
        Initialize the SocialSystem with a given configuration.

        Args:
            config (Any): Configuration settings for the system.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal state of the social system.

        This method should set up the initial state required for the system's operations.

        Returns:
            Any: The initial state of the system.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """
        Asynchronously set up the system's components.

        This method should initialize any necessary components or resources based on the provided configuration.
        """
        pass

    @abstractmethod
    async def update(self, external_input: Any) -> None:
        """
        Asynchronously update the system based on external input, such as agent actions or environmental changes.

        Args:
            external_input (Any): The data or input that influences the system's state.
        """
        pass

    @abstractmethod
    async def reset(self) -> None:
        """
        Reset the system to its initial state.

        This method can be used to restart the system, clearing or resetting the internal state.
        """
        pass

    @abstractmethod
    def get_current_state(self) -> Any:
        """
        Retrieve the current internal state of the system.

        Returns:
            Any: The current internal state of the system.
        """
        pass

    @abstractmethod
    async def interact(self, participants: Any, interaction_data: Any) -> Any:
        """
        Handle an interaction within the system, which could involve one or more agents, and possibly the environment.

        Args:
            participants (Any): The entity/entities interacting in the system. Can be a single agent, multiple agents, or agents interacting with the environment.
            interaction_data (Any): The data describing the interaction, such as communication, transaction, or other system-specific data.

        Returns:
            Any: The result of the interaction, which could be the updated state, a message, or other relevant outcome.
        """
        pass

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur within the system's operations.

        Args:
            error (Exception): The exception that was raised.
        """
        print(f"SocialSystem encountered an error: {error}")