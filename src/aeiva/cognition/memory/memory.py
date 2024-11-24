from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_link import MemoryLink


class Memory(ABC):
    """
    Abstract base class for memory operations in the intelligent agent.

    This class defines methods corresponding to different layers of memory processing,
    such as creating, filtering, grouping, deriving, structuring, skillizing, embedding,
    and parameterizing memory units.
    """

    def __init__(self, config: Any):
        """
        Initialize the Memory system with the provided configuration.

        Args:
            config (Any): Configuration settings for the Memory system.
        """
        self.config = config

    @abstractmethod
    def setup(self) -> None:
        """
        Asynchronously set up the Memory system's components.

        This method should initialize any necessary components or resources based on the provided configuration.

        Raises:
            ConfigurationError: If the configuration is invalid or incomplete.
        """
        pass

    @abstractmethod
    def create(self, content: Any, **kwargs) -> MemoryUnit:
        """
        Creates a new memory unit with the given content and metadata.

        Args:
            content (Any): The core content of the memory unit.
            **kwargs: Additional metadata for the memory unit.

        Returns:
            MemoryUnit: The created memory unit.
        """
        pass

    @abstractmethod
    def get(self, unit_id: str) -> MemoryUnit:
        """
        Retrieves a memory unit by its unique identifier.

        Args:
            unit_id (str): The unique identifier of the memory unit.

        Returns:
            MemoryUnit: The retrieved memory unit.
        """
        pass

    @abstractmethod
    def update(self, unit_id: str, updates: Dict[str, Any]) -> None:
        """
        Updates a memory unit with the given updates.

        Args:
            unit_id (str): The unique identifier of the memory unit.
            updates (Dict[str, Any]): A dictionary of fields to update.
        """
        pass

    @abstractmethod
    def delete(self, unit_id: str) -> None:
        """
        Deletes a memory unit by its unique identifier.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        pass

    @abstractmethod
    def get_all(self) -> List[MemoryUnit]:
        """
        Retrieves all memory units.

        Returns:
            List[MemoryUnit]: A list of all memory units.
        """
        pass

    @abstractmethod
    def delete_all(self) -> None:
        """
        Deletes all memory units.
        """
        pass

    @abstractmethod
    def load(self) -> None:
        """
        Loads the memory from file. The path is specified in config.
        """
        pass

    @abstractmethod
    def save(self) -> None:
        """
        Save the memory to database or file. The path is specified in config.
        """
        pass

    @abstractmethod
    def filter(self, criteria: Dict[str, Any]) -> List[MemoryUnit]:
        """
        Filters memory units based on the given criteria.

        Args:
            criteria (Dict[str, Any]): A dictionary of filter conditions.

        Returns:
            List[MemoryUnit]: A list of memory units matching the criteria.
        """
        pass

    @abstractmethod
    def organize(self, unit_ids: List[str], organize_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Groups memory units into a meaningful group.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to group.
            organize_type (str): The type of group (e.g., 'dialogue_session', 'procedure').
            metadata (Optional[Dict[str, Any]]): Additional metadata for the group.

        Returns:
            str: A unique identifier for the created group.
        """
        pass

    # @abstractmethod
    # def derive(self, unit_ids: List[str], derivation_type: str, **kwargs) -> MemoryUnit:
    #     """
    #     Derives a new memory unit from existing ones.

    #     Args:
    #         unit_ids (List[str]): A list of memory unit IDs to derive from.
    #         derivation_type (str): The type of derivation (e.g., 'summary', 'transformation').
    #         **kwargs: Additional parameters for the derivation process.

    #     Returns:
    #         MemoryUnit: The derived memory unit.
    #     """
    #     pass

    @abstractmethod
    def structurize(self, unit_ids: List[str], structure_type: str, **kwargs) -> None:
        """
        Structures memory units into a knowledge graph or other structures.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to structurize.
            structure_type (str): The type of structure (e.g., 'knowledge_graph').
            **kwargs: Additional parameters for the structuring process.
        """
        pass

    @abstractmethod
    def skillize(self, unit_ids: List[str], skill_name: str, **kwargs) -> str:
        """
        Converts memory units into a reusable skill.

        Args:
            unit_ids (List[str]): A list of memory unit IDs to skillize.
            skill_name (str): The name of the skill to create.
            **kwargs: Additional parameters for skill creation.

        Returns:
            str: The unique identifier of the created skill.
        """
        pass

    @abstractmethod
    def embed(self, unit_id: str) -> None:
        """
        Generates an embedding for a memory unit.

        Args:
            unit_id (str): The unique identifier of the memory unit.
        """
        pass

    @abstractmethod
    def parameterize(self, **kwargs) -> None:
        """
        Trains a parametric model using the memory data.

        Args:
            **kwargs: Additional parameters for the training process.
        """
        pass

    @abstractmethod
    def retrieve(self, query: Any, retrieve_type: str, **kwargs) -> List[MemoryUnit]:
        """
        Asynchronously retrieve data from memory based on a query.

        Args:
            query (Any): The query or criteria to retrieve specific memory data.
            retrieve_type (str): The type of retrieval (e.g., 'retrieve_related', 'retrieve_similar').
            **kwargs: Additional parameters for the structuring process.

        Returns:
            Any: The retrieved memory data.

        Raises:
            RetrievalError: If the retrieval process fails.
        """
        pass

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during memory operations.

        This method can be overridden to implement custom error handling logic.

        Args:
            error (Exception): The exception that was raised.
        """
        # Default error handling: log the error
        print(f"Memory system encountered an error: {error}")
