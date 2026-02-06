from abc import abstractmethod
from typing import Any, Dict, List, Optional

from aeiva.storage.database import Database


class NodeNotFoundError(Exception):
    """Exception raised when a node is not found in the graph database."""
    pass


class RelationshipNotFoundError(Exception):
    """Exception raised when a relationship is not found in the graph database."""
    pass


class StorageError(Exception):
    """Exception raised when there is a storage-related error in the graph database."""
    pass


class GraphDatabase(Database):
    """Abstract base class for graph database operations."""

    @abstractmethod
    def add_node(self, node_id: str, properties: Optional[Dict[str, Any]] = None, labels: Optional[List[str]] = None) -> None:
        """Add a node to the graph."""
        pass

    @abstractmethod
    def add_edge(self, source_id: str, target_id: str, relationship: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """Add an edge (relationship) between two nodes."""
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Dict[str, Any]:
        """Retrieve a node by its identifier."""
        pass

    @abstractmethod
    def update_node(self, node_id: str, properties: Dict[str, Any]) -> None:
        """Update properties of a node."""
        pass

    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        """Delete a node from the graph."""
        pass

    @abstractmethod
    def delete_all(self) -> None:
        """Delete all nodes and their associated relationships from the graph."""
        pass

    @abstractmethod
    def delete_all_edges(self) -> None:
        """Delete all edges from the graph without deleting the nodes."""
        pass

    @abstractmethod
    def delete_edge(self, source_id: str, target_id: str, relationship: str) -> None:
        """Delete a specific relationship between two nodes."""
        pass

    @abstractmethod
    def update_edge(self, source_id: str, target_id: str, relationship: str, properties: Dict[str, Any]) -> None:
        """Update properties of a specific relationship between two nodes."""
        pass

    @abstractmethod
    def get_relationship(self, source_id: str, target_id: str, relationship: str) -> Dict[str, Any]:
        """Retrieve a specific relationship between two nodes."""
        pass

    @abstractmethod
    def get_neighbors(self, node_id: str, relationship: Optional[str] = None, direction: str = "both") -> List[Dict[str, Any]]:
        """Retrieve neighboring nodes connected by edges."""
        pass

    @abstractmethod
    def query_nodes(self, properties: Dict[str, Any], labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Query nodes based on properties and labels."""
        pass

    @abstractmethod
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a raw query against the graph database."""
        pass
