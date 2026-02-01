"""
Simple in-memory implementation of the Memory interface.

**Test-only.** For production, use ``MemoryService``.

Provides a lightweight memory system for testing and development.
Supports pluggable storage backends.
"""

import logging
from typing import Any, Dict, List, Optional

from aeiva.cognition.memory.base_memory import Memory
from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.backend import MemoryBackend, InMemoryBackend

logger = logging.getLogger(__name__)


class SimpleMemory(Memory):
    """
    Simple in-memory implementation of the Memory interface.

    Uses pluggable backends for storage and basic keyword matching for retrieval.
    Suitable for testing, development, and simple use cases.

    Args:
        config: Optional configuration dictionary.
        backend: Optional storage backend. Defaults to InMemoryBackend.

    Example:
        # Default in-memory storage
        memory = SimpleMemory()

        # With JSON file persistence
        from aeiva.cognition.memory import JsonFileBackend
        memory = SimpleMemory(backend=JsonFileBackend("memory.json"))

        # With vector search support
        from aeiva.cognition.memory import InMemoryVectorBackend
        memory = SimpleMemory(backend=InMemoryVectorBackend())
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        backend: Optional[MemoryBackend] = None
    ):
        """
        Initialize SimpleMemory.

        Args:
            config: Optional configuration dictionary.
            backend: Optional storage backend. Defaults to InMemoryBackend.
        """
        super().__init__(config)
        self._backend = backend or InMemoryBackend()
        self._groups: Dict[str, List[str]] = {}

    def setup(self) -> None:
        """Set up the memory system."""
        logger.info(f"SimpleMemory initialized with backend: {type(self._backend).__name__}")

    async def teardown(self) -> None:
        """Clean up resources."""
        self._backend.clear()
        self._groups.clear()
        logger.info("SimpleMemory teardown complete")

    # ========== CRUD Operations ==========

    def create(self, content: Any, **kwargs) -> MemoryUnit:
        """
        Create a new memory unit.

        Args:
            content: The content to store.
            **kwargs: Additional metadata.

        Returns:
            The created MemoryUnit.
        """
        unit = MemoryUnit(content=content, **kwargs)
        self._backend.add(unit)
        logger.debug(f"Created memory unit: {unit.id}")
        return unit

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """
        Retrieve a memory unit by ID.

        Args:
            unit_id: The unique identifier.

        Returns:
            The MemoryUnit if found, None otherwise.
        """
        return self._backend.get(unit_id)

    def update(self, unit_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a memory unit.

        Args:
            unit_id: The unique identifier.
            updates: Dictionary of fields to update.

        Returns:
            True if updated, False if not found.
        """
        result = self._backend.update(unit_id, updates)
        if result:
            logger.debug(f"Updated memory unit: {unit_id}")
        return result

    def delete(self, unit_id: str) -> bool:
        """
        Delete a memory unit.

        Args:
            unit_id: The unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        result = self._backend.delete(unit_id)
        if result:
            # Also remove from any groups
            for group_ids in self._groups.values():
                if unit_id in group_ids:
                    group_ids.remove(unit_id)
            logger.debug(f"Deleted memory unit: {unit_id}")
        return result

    def get_all(self) -> List[MemoryUnit]:
        """
        Retrieve all memory units.

        Returns:
            List of all MemoryUnits.
        """
        return self._backend.get_all()

    def delete_all(self) -> int:
        """
        Delete all memory units.

        Returns:
            Number of units deleted.
        """
        count = self._backend.clear()
        self._groups.clear()
        logger.info(f"Deleted all {count} memory units")
        return count

    # ========== Persistence ==========

    def load(self, path: Optional[str] = None) -> List[MemoryUnit]:
        """
        Load memory units (returns current state for SimpleMemory).

        Args:
            path: Ignored for SimpleMemory.

        Returns:
            List of all MemoryUnits.
        """
        return self.get_all()

    def save(self, path: Optional[str] = None) -> None:
        """
        Save memory units (no-op for SimpleMemory).

        Args:
            path: Ignored for SimpleMemory.
        """
        logger.debug("SimpleMemory save called (no-op)")

    # ========== Filtering and Organization ==========

    def filter(self, criteria: Dict[str, Any]) -> List[MemoryUnit]:
        """
        Filter memory units based on criteria.

        Supported filter types:
            - by_modality: Filter by modality
            - by_type: Filter by type
            - by_tags: Filter by tags (any match)
            - by_time: Filter by timestamp range
            - by_status: Filter by status

        Args:
            criteria: Filter conditions.

        Returns:
            List of matching MemoryUnits.
        """
        filter_type = criteria.get("filter_type")
        units = self._backend.get_all()

        if filter_type == "by_modality":
            modalities = criteria.get("modalities", [])
            units = [u for u in units if u.modality in modalities]

        elif filter_type == "by_type":
            types = criteria.get("types", [])
            units = [u for u in units if u.type in types]

        elif filter_type == "by_tags":
            tags = set(criteria.get("tags", []))
            units = [u for u in units if tags.intersection(u.tags)]

        elif filter_type == "by_time":
            start = criteria.get("start_time")
            end = criteria.get("end_time")
            if start:
                units = [u for u in units if u.timestamp >= start]
            if end:
                units = [u for u in units if u.timestamp <= end]

        elif filter_type == "by_status":
            status = criteria.get("status")
            units = [u for u in units if u.status == status]

        return units

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
        import uuid
        group_id = f"group_{uuid.uuid4().hex[:8]}"
        self._groups[group_id] = list(unit_ids)
        logger.debug(f"Created group {group_id} with {len(unit_ids)} units")
        return group_id

    # ========== Embedding and Retrieval ==========

    def embed(self, unit_id: str) -> bool:
        """
        Generate embedding (no-op for SimpleMemory).

        Args:
            unit_id: The unit to embed.

        Returns:
            True (always succeeds but doesn't actually embed).
        """
        logger.debug(f"Embed called for {unit_id} (no-op in SimpleMemory)")
        return True

    def retrieve(
        self,
        query: Any,
        retrieve_type: str = "similar",
        **kwargs
    ) -> List[MemoryUnit]:
        """
        Retrieve memory units based on query.

        Supports multiple retrieval types:
        - 'similar': Keyword or semantic similarity search
        - 'related': Graph traversal via edges
        - 'vector': Vector similarity (requires VectorBackend and query_embedding)

        Args:
            query: Search query (string, ID, or embedding vector).
            retrieve_type: Type of retrieval.
            **kwargs: top_k, threshold, query_embedding, etc.

        Returns:
            List of matching MemoryUnits.
        """
        top_k = kwargs.get("top_k", 10)

        if retrieve_type == "related":
            return self._retrieve_related(query, **kwargs)

        if retrieve_type == "vector":
            return self._retrieve_vector(query, **kwargs)

        # Check if backend has keyword search
        if hasattr(self._backend, 'search_keyword'):
            return self._backend.search_keyword(str(query), top_k=top_k)

        # Default: keyword-based similarity
        query_str = str(query).lower()
        query_words = set(query_str.split())

        scored_units = []
        for unit in self._backend.get_all():
            content_str = str(unit.content).lower()
            content_words = set(content_str.split())

            # Simple word overlap scoring
            overlap = len(query_words.intersection(content_words))
            if overlap > 0:
                score = overlap / max(len(query_words), 1)
                scored_units.append((score, unit))

        # Sort by score descending
        scored_units.sort(key=lambda x: x[0], reverse=True)

        return [unit for _, unit in scored_units[:top_k]]

    def _retrieve_related(self, unit_id: str, **kwargs) -> List[MemoryUnit]:
        """Get units related to a given unit via edges."""
        relationship = kwargs.get("relationship")

        unit = self._backend.get(unit_id)
        if unit is None:
            return []

        related_ids = set()
        for edge in unit.edges:
            if relationship is None or edge.relationship == relationship:
                related_ids.add(edge.target_id)

        return [u for uid in related_ids if (u := self._backend.get(uid)) is not None]

    def _retrieve_vector(self, query: Any, **kwargs) -> List[MemoryUnit]:
        """Retrieve using vector similarity search."""
        top_k = kwargs.get("top_k", 10)
        threshold = kwargs.get("threshold", 0.0)
        query_embedding = kwargs.get("query_embedding")

        # If query is already an embedding
        if isinstance(query, list) and query and isinstance(query[0], (int, float)):
            query_embedding = query

        if query_embedding is None:
            logger.warning("Vector retrieval requires query_embedding parameter")
            return []

        # Check if backend supports vector search
        if hasattr(self._backend, 'search_similar'):
            return self._backend.search_similar(query_embedding, top_k=top_k, threshold=threshold)

        logger.warning("Backend does not support vector search")
        return []

    # ========== Convenience Methods ==========

    def store(self, content: Any, metadata: Optional[Dict[str, Any]] = None) -> MemoryUnit:
        """
        Store content with optional metadata.

        Args:
            content: Content to store.
            metadata: Optional metadata dictionary.

        Returns:
            Created MemoryUnit.
        """
        kwargs = metadata or {}
        return self.create(content, **kwargs)

    def search(self, query: str, top_k: int = 10) -> List[MemoryUnit]:
        """
        Search for memories matching query.

        Args:
            query: Search query.
            top_k: Maximum results.

        Returns:
            Matching MemoryUnits.
        """
        return self.retrieve(query, retrieve_type="similar", top_k=top_k)

    @property
    def size(self) -> int:
        """Get number of stored memory units."""
        return self._backend.count()

    @property
    def backend(self) -> MemoryBackend:
        """Get the storage backend."""
        return self._backend

    def get_current_state(self) -> List[Dict[str, Any]]:
        """
        Get current state as list of dictionaries.

        Returns:
            List of memory unit dictionaries.
        """
        return [unit.to_dict() for unit in self._backend.get_all()]

    def __len__(self) -> int:
        """Return number of stored units."""
        return self._backend.count()

    def __contains__(self, unit_id: str) -> bool:
        """Check if unit ID exists."""
        return self._backend.contains(unit_id)
