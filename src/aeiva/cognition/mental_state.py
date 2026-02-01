# File: cognition/mental_state.py

from abc import ABC, abstractmethod
from typing import Any


class MentalState(ABC):
    """
    Abstract base class representing a generic 'Mental State' subsystem of an agent.

    Each specialized mental state module (e.g., Goal, Reward, WorldModel) should inherit
    from this class and implement the abstract methods accordingly.

    Attributes:
        config (Any): Configuration for this mental state system.
        state (Any): The internal representation of the mental state.
    """

    def __init__(self, config: Any):
        """
        Initialize the MentalState system with the provided configuration.

        Args:
            config (Any): Configuration settings for this mental state system.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal representation/state for this mental state.

        Returns:
            Any: The initial internal state.
        """
        pass

    @abstractmethod
    def setup(self) -> None:
        """
        Set up the mental state system.

        This method should initialize any necessary resources or components based on self.config.
        Could raise a ConfigurationError if the config is invalid.
        """
        pass

    @abstractmethod
    async def update(self, new_data: Any) -> None:
        """
        Asynchronously update the mental state with new data.

        Args:
            new_data (Any): New information to be incorporated.

        Raises:
            UpdateError: If the update fails for any reason.
        """
        pass

    @abstractmethod
    async def query(self, query_data: Any) -> Any:
        """
        Asynchronously query the mental state for specific information.

        Args:
            query_data (Any): The query or criteria.

        Returns:
            Any: The result or information retrieved from the mental state.

        Raises:
            QueryError: If querying fails for any reason.
        """
        pass

    def get_current_state(self) -> Any:
        """
        Retrieve the current internal state of this mental state module.

        Returns:
            Any: The current internal representation/state.
        """
        return self.state

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur in mental state operations.

        This can be overridden to implement custom error handling logic.

        Args:
            error (Exception): The exception that was raised.
        """
        print(f"MentalState encountered an error: {error}")