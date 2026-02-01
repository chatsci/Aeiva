"""
Abstract base class for memory systems.

Defines the interface that all memory implementations must follow.
"""

import logging
import warnings
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from aeiva.cognition.memory.memory_unit import MemoryUnit

_logger = logging.getLogger(__name__)


class Memory(ABC):
    """
    Abstract base class for memory operations in an intelligent agent.

    This class defines the interface for memory systems, including:
    - CRUD operations for memory units
    - Filtering and organization
    - Embedding and retrieval
    - Knowledge structuring
    - Skill extraction

    Implementations should handle storage, indexing, and retrieval
    of memory units with support for various query types.
    """

    def __init__(self, config: Any = None):
        """
        Initialize the memory system.

        Args:
            config: Configuration settings for the memory system.
        """
        self.config = config

    @abstractmethod
    def setup(self) -> None:
        """
        Set up the memory system's components.

        Should initialize storage backends, embedders, and other
        required components based on configuration.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """
        Clean up resources and close connections.

        Should be called when the memory system is being shut down.
        """
        pass

    # ========== CRUD Operations ==========

    @abstractmethod
    def create(self, content: Any, **kwargs) -> MemoryUnit:
        """
        Create a new memory unit.

        Args:
            content: The content to store.
            **kwargs: Additional metadata (modality, type, tags, etc.).

        Returns:
            The created MemoryUnit.
        """
        pass

    @abstractmethod
    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """
        Retrieve a memory unit by ID.

        Args:
            unit_id: The unique identifier.

        Returns:
            The MemoryUnit if found, None otherwise.
        """
        pass

    @abstractmethod
    def update(self, unit_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a memory unit.

        Args:
            unit_id: The unique identifier.
            updates: Dictionary of fields to update.

        Returns:
            True if updated, False if not found.
        """
        pass

    @abstractmethod
    def delete(self, unit_id: str) -> bool:
        """
        Delete a memory unit.

        Args:
            unit_id: The unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abstractmethod
    def get_all(self) -> List[MemoryUnit]:
        """
        Retrieve all memory units.

        Returns:
            List of all MemoryUnits.
        """
        pass

    @abstractmethod
    def delete_all(self) -> int:
        """
        Delete all memory units.

        Returns:
            Number of units deleted.
        """
        pass

    # ========== Persistence ==========

    @abstractmethod
    def load(self, path: Optional[str] = None) -> List[MemoryUnit]:
        """
        Load memory units from storage.

        Args:
            path: Optional path to load from.

        Returns:
            List of loaded MemoryUnits.
        """
        pass

    @abstractmethod
    def save(self, path: Optional[str] = None) -> None:
        """
        Save memory units to storage.

        Args:
            path: Optional path to save to.
        """
        pass

    # ========== Filtering and Organization ==========

    @abstractmethod
    def filter(self, criteria: Dict[str, Any]) -> List[MemoryUnit]:
        """
        Filter memory units based on criteria.

        Args:
            criteria: Filter conditions (filter_type, params).

        Returns:
            List of matching MemoryUnits.
        """
        pass

    @abstractmethod
    def organize(
        self,
        unit_ids: List[str],
        organize_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Organize memory units into a group.

        Args:
            unit_ids: IDs of units to organize.
            organize_type: Type of organization.
            metadata: Additional group metadata.

        Returns:
            ID of the created group.
        """
        pass

    # ========== Embedding and Retrieval ==========

    @abstractmethod
    def embed(self, unit_id: str) -> bool:
        """
        Generate or update embedding for a memory unit.

        Args:
            unit_id: The unit to embed.

        Returns:
            True if successful.
        """
        pass

    @abstractmethod
    def retrieve(
        self,
        query: Any,
        retrieve_type: str,
        **kwargs
    ) -> List[MemoryUnit]:
        """
        Retrieve memory units based on query.

        Args:
            query: The query (text for similarity, ID for related).
            retrieve_type: Type of retrieval ('similar', 'related').
            **kwargs: Additional parameters (top_k, threshold, etc.).

        Returns:
            List of matching MemoryUnits.
        """
        pass

    # ========== Knowledge Processing (deprecated no-ops) ==========

    def structurize(
        self,
        unit_ids: List[str],
        structure_type: str,
        **kwargs
    ) -> None:
        """Deprecated: structurize is a no-op. Override in subclass if needed."""
        warnings.warn(
            "structurize() is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        _logger.debug("structurize() called — no-op")

    def skillize(
        self,
        unit_ids: List[str],
        skill_name: str,
        **kwargs
    ) -> str:
        """Deprecated: skillize is a no-op. Override in subclass if needed."""
        warnings.warn(
            "skillize() is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        _logger.debug("skillize() called — no-op")
        return ""

    def parameterize(self, **kwargs) -> None:
        """Deprecated: parameterize is a no-op. Override in subclass if needed."""
        warnings.warn(
            "parameterize() is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        _logger.debug("parameterize() called — no-op")

    # ========== Error Handling ==========

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors in memory operations.

        Can be overridden for custom error handling.

        Args:
            error: The exception that occurred.
        """
        _logger.error(f"Memory error: {error}")
