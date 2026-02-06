from abc import abstractmethod
from typing import List, Any, Optional, Dict

from aeiva.storage.database import Database


class VectorDatabase(Database):
    """Abstract base class for vector storage operations."""

    @abstractmethod
    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str) -> None:
        """Create a new vector collection."""
        pass

    @abstractmethod
    def insert_vectors(self, collection_name: str, vectors: List[List[float]], payloads: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> None:
        """Insert vectors into a collection."""
        pass

    @abstractmethod
    def search_vectors(self, collection_name: str, query_vector: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors in a collection."""
        pass

    @abstractmethod
    def delete_vector(self, collection_name: str, vector_id: str) -> None:
        """Delete a vector from a collection by its ID."""
        pass

    @abstractmethod
    def update_vector(self, collection_name: str, vector_id: str, vector: Optional[List[float]] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        """Update a vector's data or payload."""
        pass

    @abstractmethod
    def get_vector(self, collection_name: str, vector_id: str) -> Dict[str, Any]:
        """Retrieve a vector by its ID."""
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        """List all available vector collections."""
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """Delete an entire vector collection."""
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection."""
        pass
