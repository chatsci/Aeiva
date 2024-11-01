# aeiva/hypergraph/hyperedge.py

from typing import Any, Dict, Optional, Set, Iterable
from aeiva.hypergraph.exceptions import HypergraphError


class HyperEdge:
    """
    Represents a hyperedge in the hypergraph, encapsulating its properties and connected nodes.
    """

    def __init__(
        self,
        id: Any,
        nodes: Optional[Iterable[Any]] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initializes a HyperEdge.

        Parameters:
            id: Unique identifier for the hyperedge.
            nodes: (Optional) Iterable of node identifiers connected by the hyperedge.
            properties: (Optional) Dictionary of properties.
        """
        self.id: Any = id
        self.nodes: Set[Any] = set(nodes) if nodes else set()
        self.properties: Dict[str, Any] = properties.copy() if properties else {}

    def add_node(self, node_id: Any) -> None:
        """
        Adds a node to the hyperedge.

        Parameters:
            node_id: Identifier of the node to add.
        """
        self.nodes.add(node_id)

    def remove_node(self, node_id: Any) -> None:
        """
        Removes a node from the hyperedge.

        Parameters:
            node_id: Identifier of the node to remove.
        """
        if node_id in self.nodes:
            self.nodes.remove(node_id)
        else:
            raise HypergraphError(f"Node '{node_id}' not found in HyperEdge '{self.id}'.")

    def add_property(self, key: str, value: Any) -> None:
        """
        Adds or updates a property of the hyperedge.

        Parameters:
            key: Property name.
            value: Property value.
        """
        self.properties[key] = value

    def get_property(self, key: str) -> Any:
        """
        Retrieves a property of the hyperedge.

        Parameters:
            key: Property name.

        Returns:
            The value of the property.

        Raises:
            HypergraphError: If the property does not exist.
        """
        if key in self.properties:
            return self.properties[key]
        else:
            raise HypergraphError(f"Property '{key}' does not exist for HyperEdge '{self.id}'.")

    def remove_property(self, key: str) -> None:
        """
        Removes a property from the hyperedge.

        Parameters:
            key: Property name.

        Raises:
            HypergraphError: If the property does not exist.
        """
        if key in self.properties:
            del self.properties[key]
        else:
            raise HypergraphError(f"Property '{key}' does not exist for HyperEdge '{self.id}'.")
    
    def to_dict(self):
        return {
            "id": self.id,
            "nodes": self.nodes,
            "properties": self.properties
        }