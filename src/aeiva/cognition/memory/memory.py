# File: cognition/memory.py

from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """
    Abstract base class representing the Memory system of an agent.

    The Memory system is responsible for storing, retrieving, and managing the agent's
    knowledge, experiences, and historical data.

    Attributes:
        config (Any): Configuration settings for the Memory system.
        state (Any): The internal state of the Memory system.
    """

    def __init__(self, config: Any):
        """
        Initialize the Memory system with the provided configuration.

        Args:
            config (Any): Configuration settings for the Memory system.
        """
        self.config = config
        self.state = self.init_state()

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal state of the Memory system.

        This method should set up the initial state required for the Memory system's operations.

        Returns:
            Any: The initial state of the Memory system.
        """
        pass

    @abstractmethod
    async def setup(self) -> None:
        """
        Asynchronously set up the Memory system's components.

        This method should initialize any necessary components or resources based on the provided configuration.

        Raises:
            ConfigurationError: If the configuration is invalid or incomplete.
        """
        pass

    @abstractmethod
    async def retrieve(self, query: Any) -> Any:
        """
        Asynchronously retrieve data from memory based on a query.

        Args:
            query (Any): The query or criteria to retrieve specific memory data.

        Returns:
            Any: The retrieved memory data.

        Raises:
            RetrievalError: If the retrieval process fails.
        """
        pass

    @abstractmethod
    async def store(self, data: Any) -> None:
        """
        Asynchronously store data into memory.

        Args:
            data (Any): The data to be stored in memory.

        Raises:
            StorageError: If the storage process fails.
        """
        pass

    def get_current_state(self) -> Any:
        """
        Retrieve the current internal state of the Memory system.

        Returns:
            Any: The current internal state.
        """
        return self.state

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during memory operations.

        This method can be overridden to implement custom error handling logic.

        Args:
            error (Exception): The exception that was raised.
        """
        # Default error handling: log the error
        print(f"Memory system encountered an error: {error}")