from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class GraphDatabase(ABC):
    """
    Abstract base class for graph database operations.
    """

    @abstractmethod
    def add_node(self, node_id: str, properties: Optional[Dict[str, Any]] = None, labels: Optional[List[str]] = None) -> None:
        """
        Adds a node to the graph.

        Args:
            node_id (str): Unique identifier for the node.
            properties (Optional[Dict[str, Any]]): Properties associated with the node.
            labels (Optional[List[str]]): Labels or types associated with the node.

        Raises:
            StorageError: If there is an issue adding the node.
        """
        pass

    @abstractmethod
    def add_edge(self, source_id: str, target_id: str, relationship: str, properties: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds an edge (relationship) between two nodes.

        Args:
            source_id (str): Unique identifier of the source node.
            target_id (str): Unique identifier of the target node.
            relationship (str): Type of the relationship.
            properties (Optional[Dict[str, Any]]): Properties associated with the edge.

        Raises:
            NodeNotFoundError: If either the source or target node does not exist.
            StorageError: If there is an issue adding the edge.
        """
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Dict[str, Any]:
        """
        Retrieves a node by its identifier.

        Args:
            node_id (str): Unique identifier of the node.

        Returns:
            Dict[str, Any]: A dictionary containing the node's properties and labels.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue retrieving the node.
        """
        pass

    @abstractmethod
    def update_node(self, node_id: str, properties: Dict[str, Any]) -> None:
        """
        Updates properties of a node.

        Args:
            node_id (str): Unique identifier of the node.
            properties (Dict[str, Any]): Properties to update.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue updating the node.
        """
        pass

    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        """
        Deletes a node from the graph.

        Args:
            node_id (str): Unique identifier of the node.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue deleting the node.
        """
        pass

    @abstractmethod
    def get_neighbors(self, node_id: str, relationship: Optional[str] = None, direction: str = "both") -> List[Dict[str, Any]]:
        """
        Retrieves neighboring nodes connected by edges.

        Args:
            node_id (str): Unique identifier of the node.
            relationship (Optional[str]): Filter by relationship type.
            direction (str): Direction of the relationships ('in', 'out', 'both').

        Returns:
            List[Dict[str, Any]]: A list of neighboring nodes.

        Raises:
            NodeNotFoundError: If the node does not exist.
            StorageError: If there is an issue retrieving neighbors.
        """
        pass

    @abstractmethod
    def query_nodes(self, properties: Dict[str, Any], labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Queries nodes based on properties and labels.

        Args:
            properties (Dict[str, Any]): Properties to filter nodes.
            labels (Optional[List[str]]): Labels to filter nodes.

        Returns:
            List[Dict[str, Any]]: A list of nodes matching the query.

        Raises:
            StorageError: If there is an issue querying nodes.
        """
        pass

    @abstractmethod
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes a raw query against the graph database.

        Args:
            query (str): The query string.
            parameters (Optional[Dict[str, Any]]): Parameters for parameterized queries.

        Returns:
            Any: The result of the query.

        Raises:
            StorageError: If there is an issue executing the query.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Closes the graph database connection and releases resources.
        """
        pass