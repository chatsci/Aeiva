"""
Memory backend protocol and implementations.

Backends handle low-level storage operations (CRUD) while Memory
implementations handle higher-level operations (retrieval, organization).
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
import json
import logging

from aeiva.cognition.memory.memory_unit import MemoryUnit

logger = logging.getLogger(__name__)


@runtime_checkable
class MemoryBackend(Protocol):
    """
    Protocol for memory storage backends.

    Backends handle low-level storage operations. They should be
    lightweight and focused on CRUD + basic queries.

    Example implementations:
        - InMemoryBackend: Dictionary-based, no persistence
        - SqliteBackend: SQLite file-based persistence
        - VectorBackend: Vector database with similarity search
    """

    def add(self, unit: MemoryUnit) -> None:
        """Add a memory unit to storage."""
        ...

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """Get a memory unit by ID."""
        ...

    def update(self, unit_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory unit. Returns True if found and updated."""
        ...

    def delete(self, unit_id: str) -> bool:
        """Delete a memory unit. Returns True if found and deleted."""
        ...

    def get_all(self) -> List[MemoryUnit]:
        """Get all memory units."""
        ...

    def clear(self) -> int:
        """Clear all memory units. Returns count of deleted units."""
        ...

    def count(self) -> int:
        """Get the number of stored units."""
        ...

    def contains(self, unit_id: str) -> bool:
        """Check if a unit exists."""
        ...


class InMemoryBackend:
    """
    In-memory storage backend using a dictionary.

    Fast but not persistent. Good for testing and short-lived sessions.
    """

    def __init__(self):
        self._storage: Dict[str, MemoryUnit] = {}

    def add(self, unit: MemoryUnit) -> None:
        """Add a memory unit."""
        self._storage[unit.id] = unit

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        """Get a memory unit by ID."""
        return self._storage.get(unit_id)

    def update(self, unit_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory unit."""
        unit = self._storage.get(unit_id)
        if unit is None:
            return False

        for key, value in updates.items():
            if hasattr(unit, key):
                setattr(unit, key, value)

        return True

    def delete(self, unit_id: str) -> bool:
        """Delete a memory unit."""
        if unit_id in self._storage:
            del self._storage[unit_id]
            return True
        return False

    def get_all(self) -> List[MemoryUnit]:
        """Get all memory units."""
        return list(self._storage.values())

    def clear(self) -> int:
        """Clear all memory units."""
        count = len(self._storage)
        self._storage.clear()
        return count

    def count(self) -> int:
        """Get the number of stored units."""
        return len(self._storage)

    def contains(self, unit_id: str) -> bool:
        """Check if a unit exists."""
        return unit_id in self._storage

    def search_keyword(self, keyword: str, top_k: int = 10) -> List[MemoryUnit]:
        """
        Simple keyword search in content.

        Args:
            keyword: Keyword to search for.
            top_k: Maximum results.

        Returns:
            List of matching MemoryUnits.
        """
        results = []
        keyword_lower = keyword.lower()

        for unit in self._storage.values():
            content_str = str(unit.content).lower()
            if keyword_lower in content_str:
                results.append(unit)
                if len(results) >= top_k:
                    break

        return results


class JsonFileBackend(InMemoryBackend):
    """
    JSON file-based storage backend.

    Inherits all CRUD/search logic from InMemoryBackend and adds
    file persistence on every mutation.
    """

    def __init__(self, file_path: str = "memory.json"):
        super().__init__()
        self._file_path = file_path
        self._load()

    def _load(self) -> None:
        """Load from file if exists."""
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    unit = MemoryUnit.from_dict(item)
                    self._storage[unit.id] = unit
            logger.info(f"Loaded {len(self._storage)} units from {self._file_path}")
        except FileNotFoundError:
            logger.debug(f"No existing file at {self._file_path}")
        except Exception as e:
            logger.error(f"Error loading from {self._file_path}: {e}")

    def _save(self) -> None:
        """Save to file."""
        try:
            data = [unit.to_dict() for unit in self._storage.values()]
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving to {self._file_path}: {e}")

    def add(self, unit: MemoryUnit) -> None:
        super().add(unit)
        self._save()

    def update(self, unit_id: str, updates: Dict[str, Any]) -> bool:
        result = super().update(unit_id, updates)
        if result:
            self._save()
        return result

    def delete(self, unit_id: str) -> bool:
        result = super().delete(unit_id)
        if result:
            self._save()
        return result

    def clear(self) -> int:
        count = super().clear()
        self._save()
        return count


class VectorBackendMixin:
    """
    Mixin that adds vector similarity search to a backend.

    Requires the backend to have _storage dict and units to have embeddings.
    """

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[MemoryUnit]:
        """
        Search for similar memories using cosine similarity.

        Args:
            query_embedding: Query vector.
            top_k: Maximum results.
            threshold: Minimum similarity score (0-1).

        Returns:
            List of similar MemoryUnits, sorted by similarity.
        """
        if not hasattr(self, '_storage'):
            return []

        results = []

        for unit in self._storage.values():
            if unit.embedding is None:
                continue

            similarity = self._cosine_similarity(query_embedding, unit.embedding)
            if similarity >= threshold:
                results.append((similarity, unit))

        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x[0], reverse=True)
        return [unit for _, unit in results[:top_k]]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


class InMemoryVectorBackend(InMemoryBackend, VectorBackendMixin):
    """
    In-memory backend with vector similarity search support.

    Combines InMemoryBackend with VectorBackendMixin for semantic search.
    """
    pass


class JsonFileVectorBackend(JsonFileBackend, VectorBackendMixin):
    """
    JSON file backend with vector similarity search support.

    Combines JsonFileBackend with VectorBackendMixin for semantic search.
    """
    pass


class MemoryStorageBackend:
    """
    Adapter that wraps a MemoryStorage instance to conform to the
    MemoryBackend protocol.

    This bridges the external-database-backed MemoryStorage with the
    uniform MemoryBackend interface used by MemoryService.
    """

    def __init__(self, storage):
        """
        Args:
            storage: A MemoryStorage instance (vector/graph/relational).
        """
        self._storage = storage

    def add(self, unit: MemoryUnit) -> None:
        self._storage.add_memory_unit(unit)

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        try:
            return self._storage.get_memory_unit(unit_id)
        except Exception as e:
            logger.warning("MemoryStorageBackend.get(%s) failed: %s", unit_id, e)
            return None

    def update(self, unit_id: str, updates: Dict[str, Any]) -> bool:
        try:
            self._storage.update_memory_unit(unit_id, updates)
            return True
        except Exception as e:
            logger.warning("MemoryStorageBackend.update(%s) failed: %s", unit_id, e)
            return False

    def delete(self, unit_id: str) -> bool:
        try:
            self._storage.delete_memory_unit(unit_id)
            return True
        except Exception as e:
            logger.warning("MemoryStorageBackend.delete(%s) failed: %s", unit_id, e)
            return False

    def get_all(self) -> List[MemoryUnit]:
        try:
            return self._storage.get_all_memory_units()
        except Exception as e:
            logger.warning("MemoryStorageBackend.get_all() failed: %s", e)
            return []

    def clear(self) -> int:
        try:
            all_units = self.get_all()
            count = len(all_units)
            self._storage.delete_all_memory_units()
            return count
        except Exception as e:
            logger.warning("MemoryStorageBackend.clear() failed: %s", e)
            return 0

    def count(self) -> int:
        return len(self.get_all())

    def contains(self, unit_id: str) -> bool:
        return self.get(unit_id) is not None

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[MemoryUnit]:
        """Delegate similarity search to MemoryStorage's vector DB."""
        try:
            return self._storage.retrieve_similar_memory_units(query_embedding, top_k)
        except Exception as e:
            logger.warning("MemoryStorageBackend.search_similar() failed: %s", e)
            return []

    def search_related(
        self,
        unit_id: str,
        relationship: Optional[str] = None
    ) -> List[MemoryUnit]:
        """Delegate related-unit retrieval to MemoryStorage's graph DB."""
        try:
            return self._storage.retrieve_related_memory_units(unit_id, relationship)
        except Exception as e:
            logger.warning("MemoryStorageBackend.search_related(%s) failed: %s", unit_id, e)
            return []
