# aeiva/hypergraph/hypergraph.py

from typing import Any, Dict, Optional, Iterable, Set, Tuple, List, Union, Iterator
import networkx as nx
import warnings
from scipy.sparse import csr_matrix
import copy

from aeiva.hypergraph.hyperedge import HyperEdge
from aeiva.hypergraph.exceptions import HypergraphError


class Hypergraph:
    """
    A simplified Hypergraph class using dictionaries and NetworkX for management.

    Parameters
    ----------
    hyperedges : Dict[Any, Dict[str, Any]]
        A dictionary where keys are hyperedge identifiers and values are dictionaries containing:
            - 'nodes': Iterable of node identifiers connected by the hyperedge.
            - 'properties': (Optional) Dictionary of properties for the hyperedge.

    node_properties : Optional[Dict[Any, Dict[str, Any]]] = None
        A dictionary where keys are node identifiers and values are dictionaries of node properties.

    hyperedge_properties : Optional[Dict[Any, Dict[str, Any]]] = None
        A dictionary where keys are hyperedge identifiers and values are dictionaries of hyperedge properties.

    name : Optional[str] = None
        Name assigned to the hypergraph.
    """

    def __init__(
        self,
        hyperedges: Dict[Any, Dict[str, Any]],
        node_properties: Optional[Dict[Any, Dict[str, Any]]] = None,
        hyperedge_properties: Optional[Dict[Any, Dict[str, Any]]] = None,
        name: Optional[str] = None
    ):
        self.name = name
        self.graph = nx.Graph()
        self.bipartite_nodes: Set[Any] = set()

        # Initialize node and hyperedge properties using deep copies to ensure full duplication
        self.node_properties: Dict[Any, Dict[str, Any]] = copy.deepcopy(node_properties) if node_properties else {}
        self.hyperedge_properties: Dict[Any, Dict[str, Any]] = copy.deepcopy(hyperedge_properties) if hyperedge_properties else {}

        # Add hyperedges and their connections to nodes
        self.hyperedges: Dict[Any, HyperEdge] = {}
        for he_id, he_data in hyperedges.items():
            nodes = he_data.get('nodes', [])
            properties = he_data.get('properties', {})
            hyperedge = HyperEdge(id=he_id, nodes=nodes, properties=properties)
            self.hyperedges[he_id] = hyperedge

            # Add hyperedge to bipartite graph with properties
            self.graph.add_node(he_id, bipartite='hyperedge', **self.hyperedge_properties.get(he_id, {}))
            self.bipartite_nodes.add(he_id)

            # Add edges between hyperedge and nodes with node properties
            for node in hyperedge.nodes:
                if node not in self.graph:
                    self.graph.add_node(node, bipartite='node', **self.node_properties.get(node, {}))
                self.graph.add_edge(he_id, node)

    def dual(self, name: Optional[str] = None) -> "Hypergraph":
        """
        Constructs the dual of the current hypergraph by reversing the roles of nodes and hyperedges.
        
        Parameters
        ----------
        name : Optional[str], default=None
            Name for the dual hypergraph. If None, defaults to the original hypergraph's name with '_dual' appended.
        
        Returns
        -------
        Hypergraph
            A new Hypergraph instance representing the dual of the current hypergraph.
        """
        # Initialize dual hyperedges, which will correspond to original nodes
        dual_hyperedges = {}
        
        # Invert the node-hyperedge structure
        for he_id, hyperedge in self.hyperedges.items():
            for node in hyperedge.nodes:
                # Each original node becomes a hyperedge in the dual
                if node not in dual_hyperedges:
                    dual_hyperedges[node] = {'nodes': [], 'properties': self.node_properties.get(node, {})}
                # The new hyperedge (original node) connects to the original hyperedge id as a "node"
                dual_hyperedges[node]['nodes'].append(he_id)
        
        # Define node properties in the dual as the original hyperedge properties
        dual_node_properties = {he_id: self.hyperedge_properties.get(he_id, {}) for he_id in self.hyperedges}
        
        # Create and return the dual Hypergraph
        return Hypergraph(
            hyperedges=dual_hyperedges,
            node_properties=dual_node_properties,
            hyperedge_properties=self.node_properties,  # Properties of original nodes now apply to dual hyperedges
            name=name or (self.name + "_dual" if self.name else "dual")
        )
    
    def nodes(self) -> List[Any]:
        """
        Returns a list of all unique node identifiers in the hypergraph.
        
        Returns
        -------
        List[Any]
            List of node IDs.
        """
        return list(self.node_properties.keys())
    
    def node_memberships(self) -> Dict[Any, List[Any]]:
        """
        Returns a dictionary where each key is a node ID and the value is a list of hyperedge IDs that include the node.
        
        Returns
        -------
        Dict[Any, List[Any]]
            Dictionary mapping node IDs to the hyperedge IDs they belong to.
        """
        memberships = {}
        for he_id, hyperedge in self.hyperedges.items():
            for node in hyperedge.nodes:
                memberships.setdefault(node, []).append(he_id)
        return memberships

    def edges(self) -> List[Any]:
        """
        Returns a list of all hyperedge identifiers in the hypergraph.
        
        Returns
        -------
        List[Any]
            List of hyperedge IDs.
        """
        return list(self.hyperedges.keys())
    
    def edge_elements(self) -> Dict[Any, List[Any]]:
        """
        Returns a dictionary where each key is a hyperedge ID and the value is a list of node IDs within that hyperedge.
        
        Returns
        -------
        Dict[Any, List[Any]]
            Dictionary mapping hyperedge IDs to lists of node IDs they contain.
        """
        return {he_id: hyperedge.nodes for he_id, hyperedge in self.hyperedges.items()}

    def __str__(self) -> str:
        """
        String representation of the hypergraph.

        Returns
        -------
        str
            A string describing the hypergraph with its name, number of nodes, and hyperedges.
        """
        return f"Hypergraph '{self.name}' with {len(self)} nodes and {len(self.hyperedges)} hyperedges."

    def __repr__(self) -> str:
        """
        Official string representation of the hypergraph.

        Returns
        -------
        str
            A detailed string describing the hypergraph with its name, number of nodes, and hyperedges.
        """
        return (
            f"Hypergraph(name={self.name!r}, "
            f"nodes={len(self)}, hyperedges={len(self.hyperedges)})"
        )

    def __len__(self) -> int:
        """
        Returns the number of nodes in the hypergraph.

        Returns
        -------
        int
            Number of nodes.
        """
        return len(self.node_properties)

    def __iter__(self) -> Iterator[Any]:
        """
        Allows iteration over the nodes of the hypergraph.

        Yields
        ------
        Any
            Node identifiers.
        """
        return iter(self.node_properties)

    def __contains__(self, item: Any) -> bool:
        """
        Checks if a node is in the hypergraph.

        Parameters
        ----------
        item : Any
            The node identifier to check.

        Returns
        -------
        bool
            True if the node exists in the hypergraph, False otherwise.
        """
        return item in self.node_properties

    def __getitem__(self, node: Any) -> Iterable[Any]:
        """
        Retrieves the neighbors of a node in the hypergraph.

        Neighbors are nodes that share at least one hyperedge with the given node.

        Parameters
        ----------
        node : Any
            The node identifier.

        Returns
        -------
        Iterable[Any]
            An iterator over neighboring node identifiers.

        Raises
        ------
        HypergraphError
            If the node does not exist in the hypergraph.
        """
        if node not in self.node_properties:
            raise HypergraphError(f"Node '{node}' does not exist in the hypergraph.")

        # Get all hyperedges that include the node
        hyperedges = set(self.graph.neighbors(node))

        # Get all nodes connected by these hyperedges
        neighbors = set()
        for he_id in hyperedges:
            neighbors.update(self.hyperedges[he_id].nodes)

        neighbors.discard(node)  # Remove the node itself
        return neighbors

    def __eq__(self, other: Any) -> bool:
        """
        Checks if two hypergraphs are equal based on their hyperedges and nodes.

        Parameters
        ----------
        other : Any
            The other object to compare.

        Returns
        -------
        bool
            True if both hypergraphs have identical nodes and hyperedges with the same properties, False otherwise.
        """
        if not isinstance(other, Hypergraph):
            return False

        # Compare nodes and their properties
        if self.node_properties != other.node_properties:
            return False

        # Compare hyperedges and their properties
        if self.hyperedges.keys() != other.hyperedges.keys():
            return False

        for he_id in self.hyperedges:
            if self.hyperedges[he_id].nodes != other.hyperedges[he_id].nodes:
                return False
            if self.hyperedge_properties.get(he_id, {}) != other.hyperedge_properties.get(he_id, {}):
                return False

        return True

    def copy(self, name: Optional[str] = None) -> 'Hypergraph':
        """
        Creates a deep copy of the hypergraph instance.

        Parameters
        ----------
        name : Optional[str], default=None
            The name for the copied Hypergraph. If not provided, retains the original name.

        Returns
        -------
        Hypergraph
            A new Hypergraph instance that is a deep copy of the original.
        """

        # Deep copy hyperedges
        hyperedges_dict = {}
        for he_id, he in self.hyperedges.items():
            hyperedges_dict[he_id] = {
                'nodes': list(he.nodes),
                'properties': copy.deepcopy(he.properties)
            }

        # Deep copy node_properties and hyperedge_properties
        node_properties_copy = copy.deepcopy(self.node_properties)
        hyperedge_properties_copy = copy.deepcopy(self.hyperedge_properties)

        # Create a new Hypergraph instance with the copied data
        return Hypergraph(
            hyperedges=hyperedges_dict,
            node_properties=node_properties_copy,
            hyperedge_properties=hyperedge_properties_copy,
            name=name if name is not None else self.name
        )

    def deepcopy(self, name: Optional[str] = None) -> 'Hypergraph':
        """
        Creates a deep copy of the hypergraph.

        Parameters
        ----------
        name : Optional[str], default=None
            The name assigned to the cloned hypergraph. If None, defaults to the original hypergraph's name suffixed with '_clone'.

        Returns
        -------
        Hypergraph
            A deep copy of the hypergraph.
        """

        # Deep copy hyperedges
        hyperedges_copy = {
            he_id: {
                'nodes': hyperedge.nodes.copy(),
                'properties': copy.deepcopy(hyperedge.properties)
            }
            for he_id, hyperedge in self.hyperedges.items()
        }

        # Deep copy node properties
        node_properties_copy = copy.deepcopy(self.node_properties)

        # Deep copy hyperedge properties
        hyperedge_properties_copy = copy.deepcopy(self.hyperedge_properties)

        # Set name
        cloned_name = f"{self.name}_deepcopy" if name is None else name

        # Initialize the cloned hypergraph
        cloned_H = Hypergraph(
            hyperedges=hyperedges_copy,
            node_properties=node_properties_copy,
            hyperedge_properties=hyperedge_properties_copy,
            name=cloned_name
        )

        return cloned_H

    # Adding and Removing Hyperedges and Nodes
    
    def add_hyperedge(
        self,
        he_id: Any,
        nodes: Iterable[Any],
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Adds a hyperedge to the hypergraph.

        Parameters
        ----------
        he_id : Any
            Unique identifier for the hyperedge.
        nodes : Iterable[Any]
            Nodes connected by the hyperedge.
        properties : Optional[Dict[str, Any]] = None
            Properties of the hyperedge.

        Raises
        ------
        HypergraphError
            If the hyperedge ID already exists.
        """
        if he_id in self.hyperedges:
            raise HypergraphError(f"Hyperedge '{he_id}' already exists.")

        hyperedge = HyperEdge(id=he_id, nodes=nodes, properties=properties)
        self.hyperedges[he_id] = hyperedge
        self.hyperedge_properties[he_id] = copy.deepcopy(properties) if properties else {}

        # Add hyperedge to bipartite graph
        self.graph.add_node(he_id, bipartite='hyperedge', **self.hyperedge_properties[he_id])
        self.bipartite_nodes.add(he_id)

        # Add edges between hyperedge and nodes
        for node in hyperedge.nodes:
            if node not in self.graph:
                self.graph.add_node(node, bipartite='node', **self.node_properties.get(node, {}))
            self.graph.add_edge(he_id, node)

    def remove_hyperedge(self, he_id: Any) -> None:
        """
        Removes a hyperedge from the hypergraph.

        Parameters
        ----------
        he_id : Any
            Identifier of the hyperedge to remove.

        Raises
        ------
        HypergraphError
            If the hyperedge does not exist.
        """
        if he_id not in self.hyperedges:
            raise HypergraphError(f"Hyperedge '{he_id}' does not exist.")

        # Remove hyperedge from the graph, which also removes all incidences
        self.graph.remove_node(he_id)
        self.bipartite_nodes.discard(he_id)

        # Remove from internal structures
        del self.hyperedges[he_id]
        self.hyperedge_properties.pop(he_id, None)

    def add_hyperedges_from(
        self,
        hyperedges: Iterable[Union[Any, Tuple[Any, Dict[str, Any]]]],
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Adds multiple hyperedges with attributes to the hypergraph.

        Parameters
        ----------
        hyperedges : Iterable[Union[Any, Tuple[Any, Dict[str, Any]]]]
            An iterable of hyperedge identifiers or tuples of (he_id, attributes).
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the added hyperedges.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If any hyperedge ID already exists.
        ValueError
            If any tuple does not contain exactly two elements or if attributes are not dictionaries.
        """
        new_hyperedges = []
        for item in hyperedges:
            if isinstance(item, tuple):
                if len(item) != 2 or not isinstance(item[1], dict):
                    raise ValueError(f"Each tuple must be of the form (he_id, attributes). Invalid tuple: {item}")
                he_id, attrs = item
            else:
                he_id, attrs = item, {}

            if he_id in self.hyperedges:
                raise HypergraphError(f"Hyperedge '{he_id}' already exists.")

            hyperedge = HyperEdge(id=he_id, nodes=[], properties=attrs.copy())
            new_hyperedges.append(hyperedge)

        if inplace:
            for hyperedge in new_hyperedges:
                self.hyperedges[hyperedge.id] = hyperedge
                self.hyperedge_properties[hyperedge.id] = copy.deepcopy(hyperedge.properties)
                self.graph.add_node(hyperedge.id, bipartite='hyperedge', **self.hyperedge_properties[hyperedge.id])
                self.bipartite_nodes.add(hyperedge.id)
            return self
        else:
            # Create a new Hypergraph instance with added hyperedges
            new_hyperedges_dict = copy.deepcopy(self.hyperedges)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            for hyperedge in new_hyperedges:
                new_hyperedges_dict[hyperedge.id] = hyperedge
                new_hyperedge_properties[hyperedge.id] = copy.deepcopy(hyperedge.properties)
                new_graph.add_node(hyperedge.id, bipartite='hyperedge', **new_hyperedge_properties[hyperedge.id])
                new_bipartite_nodes.add(hyperedge.id)

            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges_dict.items()
            }

            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    def add_node(
        self,
        node_id: Any,
        properties: Optional[Dict[str, Any]] = None,
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Adds a node to the hypergraph.

        Parameters
        ----------
        node_id : Any
            Identifier for the node.
        properties : Optional[Dict[str, Any]] = None
            Properties of the node.
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the added node.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If the node ID already exists.
        """
        if node_id in self.node_properties:
            raise HypergraphError(f"Node '{node_id}' already exists in the hypergraph.")

        if inplace:
            self.node_properties[node_id] = copy.deepcopy(properties) if properties else {}
            self.graph.add_node(node_id, bipartite='node', **self.node_properties[node_id])
            return self
        else:
            # Create a new Hypergraph instance with the added node
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            new_node_properties[node_id] = copy.deepcopy(properties) if properties else {}
            new_graph.add_node(node_id, bipartite='node', **new_node_properties[node_id])

            return Hypergraph(
                hyperedges={
                    he_id: {
                        'nodes': list(he.nodes),
                        'properties': he.properties.copy()
                    } for he_id, he in new_hyperedges.items()
                },
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    def remove_node(self, node_id: Any, inplace: bool = True) -> 'Hypergraph':
        """
        Removes a node from the hypergraph.

        Parameters
        ----------
        node_id : Any
            Identifier of the node to remove.
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the node removed.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If the node does not exist.
        """
        if node_id not in self.node_properties:
            raise HypergraphError(f"Node '{node_id}' does not exist in the hypergraph.")

        if inplace:
            # Remove node from node_properties
            del self.node_properties[node_id]
            # Remove node from all hyperedges
            for hyperedge in self.hyperedges.values():
                if node_id in hyperedge.nodes:
                    hyperedge.remove_node(node_id)
            # Remove node from graph, which also removes all incidences
            self.graph.remove_node(node_id)
            return self
        else:
            # Create a new Hypergraph instance with the node removed
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            # Remove node from node_properties
            del new_node_properties[node_id]
            # Remove node from all hyperedges
            for hyperedge in new_hyperedges.values():
                if node_id in hyperedge.nodes:
                    hyperedge.remove_node(node_id)
            # Remove node from graph, which also removes all incidences
            new_graph.remove_node(node_id)

            # Remove nodes not connected to any hyperedges
            retained_nodes = set()
            for hyperedge in new_hyperedges.values():
                retained_nodes.update(hyperedge.nodes)

            new_node_properties = {node: props for node, props in new_node_properties.items() if node in retained_nodes}

            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            }

            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    def add_nodes_from(
        self,
        nodes: Iterable[Union[Any, Tuple[Any, Dict[str, Any]]]],
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Adds multiple nodes with attributes to the hypergraph.

        Parameters
        ----------
        nodes : Iterable[Union[Any, Tuple[Any, Dict[str, Any]]]]
            An iterable of node identifiers or tuples of (node_id, attributes).
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the added nodes.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If any node ID already exists.
        ValueError
            If any tuple does not contain exactly two elements or if attributes are not dictionaries.
        """
        new_nodes = {}
        for item in nodes:
            if isinstance(item, tuple):
                if len(item) != 2 or not isinstance(item[1], dict):
                    raise ValueError(f"Each tuple must be of the form (node_id, attributes). Invalid tuple: {item}")
                node_id, attrs = item
            else:
                node_id, attrs = item, {}

            if node_id in self.node_properties:
                raise HypergraphError(f"Node '{node_id}' already exists in the hypergraph.")

            new_nodes[node_id] = copy.deepcopy(attrs)

        if inplace:
            for node_id, attrs in new_nodes.items():
                self.node_properties[node_id] = attrs
                self.graph.add_node(node_id, bipartite='node', **self.node_properties[node_id])
            return self
        else:
            # Create a new Hypergraph instance with the added nodes
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            for node_id, attrs in new_nodes.items():
                new_node_properties[node_id] = attrs
                new_graph.add_node(node_id, bipartite='node', **new_node_properties[node_id])

            return Hypergraph(
                hyperedges={
                    he_id: {
                        'nodes': list(he.nodes),
                        'properties': he.properties.copy()
                    } for he_id, he in new_hyperedges.items()
                },
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    def remove_hyperedges(self, he_ids: Union[Any, Iterable[Any]], inplace: bool = True) -> 'Hypergraph':
        """
        Removes the specified hyperedges from the hypergraph.

        Parameters
        ----------
        he_ids : Any | Iterable[Any]
            Hyperedge identifier(s) to remove.
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the hyperedges removed.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If any hyperedge ID does not exist.
        """
        if isinstance(he_ids, (str, int)):
            he_ids = [he_ids]
        else:
            he_ids = list(he_ids)

        non_existing = set(he_ids) - set(self.hyperedges.keys())
        if non_existing:
            raise HypergraphError(f"Hyperedges {non_existing} do not exist in the hypergraph.")

        if inplace:
            for he_id in he_ids:
                self.remove_hyperedge(he_id)
            return self
        else:
            # Create a new Hypergraph instance with hyperedges removed
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            for he_id in he_ids:
                del new_hyperedges[he_id]
                new_hyperedge_properties.pop(he_id, None)
                new_graph.remove_node(he_id)
                new_bipartite_nodes.discard(he_id)

            # Remove nodes not connected to any hyperedges
            retained_nodes = set()
            for hyperedge in new_hyperedges.values():
                retained_nodes.update(hyperedge.nodes)

            new_node_properties = {node: props for node, props in new_node_properties.items() if node in retained_nodes}

            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            }

            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    def remove_nodes_from(
        self,
        nodes: Union[Any, Iterable[Any]],
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Removes the specified nodes from the hypergraph.

        Parameters
        ----------
        nodes : Any | Iterable[Any]
            Node identifier(s) to remove.
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the nodes removed.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If any node ID does not exist.
        """
        if isinstance(nodes, (str, int)):
            nodes = [nodes]
        else:
            nodes = list(nodes)

        non_existing = set(nodes) - set(self.node_properties.keys())
        if non_existing:
            raise HypergraphError(f"Nodes {non_existing} do not exist in the hypergraph.")

        if inplace:
            for node_id in nodes:
                self.remove_node(node_id)
            return self
        else:
            # Create a new Hypergraph instance with nodes removed
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            for node_id in nodes:
                del new_node_properties[node_id]
                # Remove node from all hyperedges
                for hyperedge in new_hyperedges.values():
                    if node_id in hyperedge.nodes:
                        hyperedge.remove_node(node_id)
                # Remove node from graph, which also removes all incidences
                new_graph.remove_node(node_id)

            # Remove nodes not connected to any hyperedges
            retained_nodes = set()
            for hyperedge in new_hyperedges.values():
                retained_nodes.update(hyperedge.nodes)

            new_node_properties = {node: props for node, props in new_node_properties.items() if node in retained_nodes}

            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            }

            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    def add_incidence(
        self,
        he_id: Any,
        node_id: Any,
        attributes: Optional[Dict[str, Any]] = None,
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Adds a single incidence with attributes to the hypergraph.

        Parameters
        ----------
        he_id : Any
            Identifier of the hyperedge.
        node_id : Any
            Identifier of the node.
        attributes : Optional[Dict[str, Any]] = None
            Properties to add to the incidence as key-value pairs.
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the added incidence.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If the hyperedge or node does not exist, or if the incidence already exists.
        """
        if he_id not in self.hyperedges:
            raise HypergraphError(f"Hyperedge '{he_id}' does not exist in the hypergraph.")
        if node_id not in self.node_properties:
            raise HypergraphError(f"Node '{node_id}' does not exist in the hypergraph.")
        if node_id in self.hyperedges[he_id].nodes:
            raise HypergraphError(f"Incidence between hyperedge '{he_id}' and node '{node_id}' already exists.")

        if inplace:
            # Add node to HyperEdge's nodes
            self.hyperedges[he_id].add_node(node_id)
            # Update hyperedge_properties if attributes provided
            if attributes:
                self.hyperedge_properties[he_id].update(attributes)
            # Add edge in graph with attributes
            self.graph.add_edge(he_id, node_id, **(attributes if attributes else {}))
            return self
        else:
            # Create a new Hypergraph instance with the incidence added
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            # Add node to HyperEdge's nodes
            new_hyperedges[he_id].add_node(node_id)
            # Update hyperedge_properties if attributes provided
            if attributes:
                new_hyperedge_properties[he_id].update(attributes)
            # Add edge in graph with attributes
            new_graph.add_edge(he_id, node_id, **(attributes if attributes else {}))

            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            }

            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    def remove_incidence(
        self,
        he_id: Any,
        node_id: Any,
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Removes a single incidence from the hypergraph.

        Parameters
        ----------
        he_id : Any
            Identifier of the hyperedge.
        node_id : Any
            Identifier of the node.
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the incidence removed.

        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.

        Raises
        ------
        HypergraphError
            If the hyperedge or node does not exist, or if the incidence does not exist.
        """
        if he_id not in self.hyperedges:
            raise HypergraphError(f"Hyperedge '{he_id}' does not exist in the hypergraph.")
        if node_id not in self.node_properties:
            raise HypergraphError(f"Node '{node_id}' does not exist in the hypergraph.")
        if node_id not in self.hyperedges[he_id].nodes:
            raise HypergraphError(f"Incidence between hyperedge '{he_id}' and node '{node_id}' does not exist.")

        if inplace:
            # Remove node from HyperEdge's nodes
            self.hyperedges[he_id].remove_node(node_id)
            # Remove edge from graph
            self.graph.remove_edge(he_id, node_id)
            return self
        else:
            # Create a new Hypergraph instance with the incidence removed
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)

            # Remove node from HyperEdge's nodes
            new_hyperedges[he_id].remove_node(node_id)
            # Remove edge from graph
            new_graph.remove_edge(he_id, node_id)

            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            }

            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )

    # Managing Properties and Incidences

    def adjacency_matrix(self, s: int = 1, index: bool = False) -> Tuple[Optional[csr_matrix], Dict[int, Any]]:
        """
        Generates the adjacency matrix for nodes based on s-node connectivity.
        """
        from scipy.sparse import lil_matrix

        node_ids = list(self.node_properties.keys())
        node_index = {node_id: idx for idx, node_id in enumerate(node_ids)}
        size = len(node_ids)
        if size == 0:
            return None, {}

        A = lil_matrix((size, size), dtype=int)
        for he in self.hyperedges.values():
            nodes = list(he.nodes)
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    A[node_index[nodes[i]], node_index[nodes[j]]] += 1

        # Apply the threshold s and convert to binary
        A = (A >= s).astype(int)
        A = A.tocsr()

        if index:
            return A, node_index
        return A, {}
    
    def hyperedge_adjacency_matrix(self, s: int = 1, index: bool = False) -> Tuple[Optional[csr_matrix], Dict[int, Any]]:
        """
        Generates the adjacency matrix for hyperedges based on s-hyperedge connectivity.

        Parameters
        ----------
        s : int, optional, default=1
            The number of shared nodes required for hyperedges to be considered adjacent.
        index : bool, optional, default=False
            If True, returns a mapping from matrix indices to hyperedge IDs.

        Returns
        -------
        Tuple[Optional[csr_matrix], Dict[int, Any]]
            - The adjacency matrix in CSR format.
            - A dictionary mapping matrix indices to hyperedge IDs.
        """
        from scipy.sparse import lil_matrix

        hyperedge_ids = list(self.hyperedges.keys())
        he_index = {he_id: idx for idx, he_id in enumerate(hyperedge_ids)}
        size = len(hyperedge_ids)
        if size == 0:
            return None, {}

        A = lil_matrix((size, size), dtype=int)
        for i, he1 in enumerate(hyperedge_ids):
            nodes1 = self.hyperedges[he1].nodes
            for j in range(i + 1, size):
                he2 = hyperedge_ids[j]
                nodes2 = self.hyperedges[he2].nodes
                shared_nodes = nodes1 & nodes2
                if len(shared_nodes) >= s:
                    A[i, j] = 1
                    A[j, i] = 1

        A = A.tocsr()

        if index:
            return A, he_index
        return A, {}

    def get_hyperedges_of_node(self, node_id: Any) -> Set[Any]:
        """
        Retrieves all hyperedges that a given node is part of.

        Parameters
        ----------
        node_id : Any
            The node identifier.

        Returns
        -------
        Set[Any]
            A set of hyperedge IDs that the node belongs to.

        Raises
        ------
        HypergraphError
            If the node does not exist in the hypergraph.
        """
        if node_id not in self.node_properties:
            raise HypergraphError(f"Node '{node_id}' does not exist in the hypergraph.")
        return {he.id for he in self.hyperedges.values() if node_id in he.nodes}
    
    def collapse_duplicate_hyperedges(
        self,
        name: Optional[str] = None,
        use_uids: Optional[List[Any]] = None,
        use_counts: bool = False,
        return_counts: bool = True,
        return_equivalence_classes: bool = False,
        aggregate_properties_by: Optional[Dict[str, str]] = None,
    ) -> Union['Hypergraph', Tuple['Hypergraph', Dict[Any, Set[Any]]]]:
        """
        Collapses duplicate hyperedges (hyperedges with identical node memberships) into single hyperedges.
    
        Parameters
        ----------
        name : Optional[str], default=None
            The name assigned to the collapsed hypergraph. If None, defaults to the original name suffixed with '_collapsed_hyperedges'.
        
        use_uids : Optional[List[Any]] = None
            Specifies the hyperedge identifiers to use as representatives for each equivalence class.
            If two identifiers occur in the same equivalence class, the first one found in `use_uids` is used.
            If None, the first encountered hyperedge in each class is used as the representative.
        
        use_counts : bool, optional, default=False
            If True, renames the equivalence class representatives by appending the size of the class (e.g., 'HE1:3').
        
        return_counts : bool, optional, default=True
            If True, adds the size of each equivalence class to the properties of the representative hyperedge under the key 'equivalence_class_size'.
        
        return_equivalence_classes : bool, optional, default=False
            If True, returns a tuple containing the new collapsed hypergraph and a dictionary mapping representatives to their equivalence classes.
        
        aggregate_properties_by : Optional[Dict[str, str]] = None
            A dictionary specifying aggregation methods for hyperedge properties. Keys are property names, and values are aggregation functions (e.g., {'weight': 'sum'}).
            Properties not specified will use the 'first' aggregation.
        
        Returns
        -------
        Hypergraph or Tuple[Hypergraph, Dict[Any, Set[Any]]]
            - If `return_equivalence_classes=False`, returns the new collapsed hypergraph.
            - If `return_equivalence_classes=True`, returns a tuple containing the collapsed hypergraph and a dictionary of equivalence classes.
        
        Raises
        ------
        HypergraphError
            If the hypergraph is empty or improperly structured.
        """
        if not self.hyperedges:
            raise HypergraphError("Cannot collapse hyperedges in an empty hypergraph.")
        
        # Identify equivalence classes based on identical node memberships
        membership_to_hyperedges: Dict[frozenset, Set[Any]] = {}
        for he_id, hyperedge in self.hyperedges.items():
            key = frozenset(hyperedge.nodes)
            membership_to_hyperedges.setdefault(key, set()).add(he_id)
        
        # Filter out classes with only one hyperedge (no duplicates)
        equivalence_classes = [hes for hes in membership_to_hyperedges.values() if len(hes) > 1]
        if not equivalence_classes:
            # No duplicates to collapse; return the original hypergraph
            return self if not return_equivalence_classes else (self, {})
        
        # Prepare aggregation methods
        aggregate_properties_by = aggregate_properties_by if aggregate_properties_by is not None else {"weight": "sum"}
        
        # Initialize mapping from old hyperedges to new hyperedges
        hyperedge_mapping: Dict[Any, Any] = {}
        equivalence_class_dict: Dict[Any, Set[Any]] = {}
        
        for eq_class in equivalence_classes:
            # Determine representative
            if use_uids:
                # Select the first UID from use_uids that is in the equivalence class
                representative = next((uid for uid in use_uids if uid in eq_class), None)
                if not representative:
                    # Fallback to the first hyperedge in the equivalence class
                    representative = next(iter(eq_class))
            else:
                # Use the first hyperedge in the equivalence class as representative
                representative = next(iter(eq_class))
            
            # Optionally rename with counts
            if use_counts:
                new_representative = f"{representative}:{len(eq_class)}"
            else:
                new_representative = representative
            
            # Map all hyperedges in the class to the representative
            for he in eq_class:
                hyperedge_mapping[he] = new_representative
            
            # Store the equivalence class
            equivalence_class_dict[new_representative] = eq_class
        
        # Replace hyperedge IDs in incidences based on mapping
        new_hyperedges = {}
        for he_id, hyperedge in self.hyperedges.items():
            new_he_id = hyperedge_mapping.get(he_id, he_id)
            if new_he_id not in new_hyperedges:
                new_hyperedges[new_he_id] = HyperEdge(id=new_he_id, nodes=hyperedge.nodes.copy(), properties=copy.deepcopy(hyperedge.properties))
            else:
                new_hyperedges[new_he_id].nodes.update(hyperedge.nodes)
        
        # Aggregate hyperedge properties
        for he_id, hyperedge in new_hyperedges.items():
            if he_id in equivalence_class_dict:
                aggregated_props = {}
                for prop, agg_func in aggregate_properties_by.items():
                    values = [self.hyperedge_properties[old_he].get(prop, 0) for old_he in equivalence_class_dict[he_id]]
                    if agg_func == 'sum':
                        aggregated_props[prop] = sum(values)
                    elif agg_func == 'mean':
                        aggregated_props[prop] = sum(values) / len(values) if values else 0
                    elif agg_func == 'max':
                        aggregated_props[prop] = max(values) if values else None
                    elif agg_func == 'min':
                        aggregated_props[prop] = min(values) if values else None
                    else:
                        aggregated_props[prop] = values[0] if values else None  # Default to first
                new_hyperedges[he_id].properties.update(aggregated_props)
        
        # Handle equivalence class size
        if use_counts:
            for he_id in equivalence_class_dict:
                new_hyperedges[he_id].properties['equivalence_class_size'] = len(equivalence_class_dict[he_id])
        elif return_counts:
            for he_id in new_hyperedges:
                if he_id in equivalence_class_dict:
                    new_hyperedges[he_id].properties['equivalence_class_size'] = len(equivalence_class_dict[he_id])
                else:
                    new_hyperedges[he_id].properties['equivalence_class_size'] = 1
        
        # Initialize the collapsed hypergraph
        collapsed_hypergraph = Hypergraph(
            hyperedges={
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            },
            node_properties=copy.deepcopy(self.node_properties),
            hyperedge_properties={
                he_id: copy.deepcopy(he.properties) for he_id, he in new_hyperedges.items()
            },
            name=name if name else f"{self.name}_collapsed_hyperedges"
        )
        
        if return_equivalence_classes:
            return collapsed_hypergraph, equivalence_class_dict
        else:
            return collapsed_hypergraph
    
    def restrict_to_specific_hyperedges(
        self,
        hyperedges_to_retain: Iterable[Any],
        name: Optional[str] = None
    ) -> 'Hypergraph':
        """
        Creates a new hypergraph by retaining only the specified hyperedges and removing all others.
    
        Parameters
        ----------
        hyperedges_to_retain : Iterable[Any]
            An iterable of hyperedge identifiers to retain in the new hypergraph.
        
        name : Optional[str], default=None
            The name assigned to the restricted hypergraph. If None, defaults to the original name suffixed with '_restricted_hyperedges'.
    
        Returns
        -------
        Hypergraph
            A new hypergraph containing only the specified hyperedges and their associated nodes.
    
        Raises
        ------
        HypergraphError
            If none of the specified hyperedges exist in the hypergraph.
        """
        hyperedges_to_retain = set(hyperedges_to_retain)
        existing_hyperedges = set(self.hyperedges.keys())
        invalid_hyperedges = hyperedges_to_retain - existing_hyperedges
        if invalid_hyperedges:
            raise HypergraphError(f"The following hyperedges do not exist and cannot be retained: {invalid_hyperedges}")
        
        # Determine hyperedges to remove
        hyperedges_to_remove = existing_hyperedges - hyperedges_to_retain
        if not hyperedges_to_remove:
            # No hyperedges to remove; return the original hypergraph
            return self
        
        # Remove hyperedges using the existing remove_hyperedges method
        restricted_hypergraph = self.remove_hyperedges(hyperedges_to_remove, inplace=False)
        restricted_hypergraph.name = name if name else f"{self.name}_restricted_hyperedges"
        
        return restricted_hypergraph
    
    def restrict_to_specific_nodes(
        self,
        nodes_to_retain: Iterable[Any],
        name: Optional[str] = None
    ) -> 'Hypergraph':
        """
        Creates a new hypergraph by retaining only the specified nodes and removing all others.
    
        Parameters
        ----------
        nodes_to_retain : Iterable[Any]
            An iterable of node identifiers to retain in the new hypergraph.
        
        name : Optional[str], default=None
            The name assigned to the restricted hypergraph. If None, defaults to the original name suffixed with '_restricted_nodes'.
    
        Returns
        -------
        Hypergraph
            A new hypergraph containing only the specified nodes and their associated hyperedges.
    
        Raises
        ------
        HypergraphError
            If none of the specified nodes exist in the hypergraph.
        """
        nodes_to_retain = set(nodes_to_retain)
        existing_nodes = set(self.node_properties.keys())
        invalid_nodes = nodes_to_retain - existing_nodes
        if invalid_nodes:
            raise HypergraphError(f"The following nodes do not exist and cannot be retained: {invalid_nodes}")
        
        # Determine nodes to remove
        nodes_to_remove = existing_nodes - nodes_to_retain
        if not nodes_to_remove:
            # No nodes to remove; return the original hypergraph
            return self
        
        # Remove nodes using the existing remove_nodes_from method
        restricted_hypergraph = self.remove_nodes_from(nodes_to_remove, inplace=False)
        restricted_hypergraph.name = name if name else f"{self.name}_restricted_nodes"
        
        return restricted_hypergraph
    
    def add_incidences_from(
        self,
        incidences: Iterable[Union[Tuple[Any, Any], Tuple[Any, Any, Dict[str, Any]]]],
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Adds a collection of incidences to the hypergraph.
    
        Parameters
        ----------
        incidences : Iterable[Union[Tuple[Any, Any], Tuple[Any, Any, Dict[str, Any]]]]
            Incidence tuples as:
                - (he_id, node_id)
                - (he_id, node_id, attributes)
        
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the added incidences.
    
        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.
    
        Raises
        ------
        HypergraphError
            If any hyperedge or node does not exist, or if any incidence already exists.
        ValueError
            If the structure of any incidence tuple is invalid.
        """
        new_incidences = []
        for pr in incidences:
            if not isinstance(pr, tuple):
                raise ValueError(f"Each incidence must be a tuple, got {type(pr)}")
            if len(pr) == 2:
                he_id, node_id = pr
                attrs = {}
            elif len(pr) == 3:
                he_id, node_id, attrs = pr
                if not isinstance(attrs, dict):
                    raise ValueError(f"Attributes must be a dictionary, got {type(attrs)}")
            else:
                raise ValueError(f"Incidence tuples must be of length 2 or 3, got {len(pr)}")
            
            if he_id not in self.hyperedges:
                raise HypergraphError(f"Hyperedge '{he_id}' does not exist in the hypergraph.")
            if node_id not in self.node_properties:
                raise HypergraphError(f"Node '{node_id}' does not exist in the hypergraph.")
            if node_id in self.hyperedges[he_id].nodes:
                raise HypergraphError(f"Incidence between hyperedge '{he_id}' and node '{node_id}' already exists.")
            
            new_incidences.append((he_id, node_id, attrs.copy()))
    
        if inplace:
            for he_id, node_id, attrs in new_incidences:
                # Add node to HyperEdge's nodes
                self.hyperedges[he_id].add_node(node_id)
                # Update hyperedge_properties if attributes provided
                if attrs:
                    self.hyperedge_properties[he_id].update(attrs)
                # Add edge in graph with attributes
                self.graph.add_edge(he_id, node_id, **(attrs if attrs else {}))
            return self
        else:
            # Create a new Hypergraph instance with the incidences added
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)
    
            for he_id, node_id, attrs in new_incidences:
                # Add node to HyperEdge's nodes
                new_hyperedges[he_id].add_node(node_id)
                # Update hyperedge_properties if attributes provided
                if attrs:
                    new_hyperedge_properties[he_id].update(attrs)
                # Add edge in graph with attributes
                new_graph.add_edge(he_id, node_id, **(attrs if attrs else {}))
    
            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            }
    
            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )
    
    def remove_incidences(
        self,
        incidences: Iterable[Tuple[Any, Any]],
        inplace: bool = True
    ) -> 'Hypergraph':
        """
        Removes the specified incidences from the hypergraph.
    
        Parameters
        ----------
        incidences : Iterable[Tuple[Any, Any]]
            Incidence identifiers as tuples of (he_id, node_id).
        inplace : bool, default=True
            If True, modifies the existing Hypergraph. Otherwise, creates a new Hypergraph with the incidences removed.
    
        Returns
        -------
        Hypergraph
            The updated or new Hypergraph instance.
    
        Raises
        ------
        HypergraphError
            If any incidence does not exist.
        """
        incidence_ids = list(incidences)
        
        # Check existence of incidences
        for he_id, node_id in incidence_ids:
            if he_id not in self.hyperedges:
                raise HypergraphError(f"Hyperedge '{he_id}' does not exist in the hypergraph.")
            if node_id not in self.node_properties:
                raise HypergraphError(f"Node '{node_id}' does not exist in the hypergraph.")
            if node_id not in self.hyperedges[he_id].nodes:
                raise HypergraphError(f"Incidence between hyperedge '{he_id}' and node '{node_id}' does not exist.")
    
        if inplace:
            for he_id, node_id in incidence_ids:
                # Remove node from HyperEdge's nodes
                self.hyperedges[he_id].remove_node(node_id)
                # Remove edge from graph
                self.graph.remove_edge(he_id, node_id)
            return self
        else:
            # Create a new Hypergraph instance with the incidences removed
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)
    
            for he_id, node_id in incidence_ids:
                # Remove node from HyperEdge's nodes
                new_hyperedges[he_id].remove_node(node_id)
                # Remove edge from graph
                new_graph.remove_edge(he_id, node_id)
    
            # Reconstruct hyperedges dict for __init__
            hyperedges_dict = {
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            }
    
            return Hypergraph(
                hyperedges=hyperedges_dict,
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=self.name
            )
    
    def collapse_duplicate_nodes(
        self,
        name: Optional[str] = None,
        use_uids: Optional[List[Any]] = None,
        use_counts: bool = False,
        return_counts: bool = True,
        return_equivalence_classes: bool = False,
        aggregate_properties_by: Optional[Dict[str, str]] = None,
    ) -> Union['Hypergraph', Tuple['Hypergraph', Dict[Any, Set[Any]]]]:
        """
        Collapses duplicate nodes (nodes with identical hyperedge memberships) into single nodes.
    
        Parameters
        ----------
        name : Optional[str], default=None
            The name assigned to the collapsed hypergraph. If None, defaults to the original name suffixed with '_collapsed_nodes'.
        
        use_uids : Optional[List[Any]] = None
            Specifies the node identifiers to use as representatives for each equivalence class.
            If two identifiers occur in the same equivalence class, the first one found in `use_uids` is used.
            If None, the first encountered node in each class is used as the representative.
        
        use_counts : bool, optional, default=False
            If True, renames the equivalence class representatives by appending the size of the class (e.g., 'N1:3').
        
        return_counts : bool, optional, default=True
            If True, adds the size of each equivalence class to the properties of the representative node under the key 'equivalence_class_size'.
        
        return_equivalence_classes : bool, optional, default=False
            If True, returns a tuple containing the new collapsed hypergraph and a dictionary mapping representatives to their equivalence classes.
        
        aggregate_properties_by : Optional[Dict[str, str]] = None
            A dictionary specifying aggregation methods for node properties. Keys are property names, and values are aggregation functions (e.g., {'weight': 'sum'}).
            Properties not specified will use the 'first' aggregation.
        
        Returns
        -------
        Hypergraph or Tuple[Hypergraph, Dict[Any, Set[Any]]]
            - If `return_equivalence_classes=False`, returns the new collapsed hypergraph.
            - If `return_equivalence_classes=True`, returns a tuple containing the collapsed hypergraph and a dictionary of equivalence classes.
        
        Raises
        ------
        HypergraphError
            If the hypergraph is empty or improperly structured.
        """
        if not self.node_properties:
            raise HypergraphError("Cannot collapse nodes in an empty hypergraph.")
        
        # Identify equivalence classes based on identical hyperedge memberships
        membership_to_nodes: Dict[frozenset, Set[Any]] = {}
        for node_id, node_props in self.node_properties.items():
            key = frozenset(self.get_hyperedges_of_node(node_id))
            membership_to_nodes.setdefault(key, set()).add(node_id)
        
        # Filter out classes with only one node (no duplicates)
        equivalence_classes = [nodes for nodes in membership_to_nodes.values() if len(nodes) > 1]
        if not equivalence_classes:
            # No duplicates to collapse; return the original hypergraph
            return self if not return_equivalence_classes else (self, {})
        
        # Prepare aggregation methods
        aggregate_properties_by = aggregate_properties_by if aggregate_properties_by is not None else {"weight": "sum"}
        
        # Initialize mapping from old nodes to new nodes
        node_mapping: Dict[Any, Any] = {}
        equivalence_class_dict: Dict[Any, Set[Any]] = {}
        
        for eq_class in equivalence_classes:
            # Determine representative
            if use_uids:
                # Select the first UID from use_uids that is in the equivalence class
                representative = next((uid for uid in use_uids if uid in eq_class), None)
                if not representative:
                    # Fallback to the first node in the equivalence class
                    representative = next(iter(eq_class))
            else:
                # Use the first node in the equivalence class as representative
                representative = next(iter(eq_class))
            
            # Optionally rename with counts
            if use_counts:
                new_representative = f"{representative}:{len(eq_class)}"
            else:
                new_representative = representative
            
            # Map all nodes in the class to the representative
            for node in eq_class:
                node_mapping[node] = new_representative
            
            # Store the equivalence class
            equivalence_class_dict[new_representative] = eq_class
        
        # Replace node IDs in hyperedges based on mapping
        new_hyperedges = {}
        for he_id, hyperedge in self.hyperedges.items():
            new_nodes = set()
            for node_id in hyperedge.nodes:
                new_node_id = node_mapping.get(node_id, node_id)
                new_nodes.add(new_node_id)
            new_hyperedges[he_id] = HyperEdge(id=he_id, nodes=new_nodes, properties=copy.deepcopy(hyperedge.properties))
        
        # Aggregate node properties
        new_node_properties = {}
        for node_id, node_props in self.node_properties.items():
            new_node_id = node_mapping.get(node_id, node_id)
            if new_node_id not in new_node_properties:
                new_node_properties[new_node_id] = copy.deepcopy(node_props)
            else:
                for prop, agg_func in aggregate_properties_by.items():
                    if prop in node_props:
                        if agg_func == 'sum':
                            new_node_properties[new_node_id][prop] = new_node_properties[new_node_id].get(prop, 0) + node_props[prop]
                        elif agg_func == 'mean':
                            # To calculate mean, store sum and count
                            if 'sum_' + prop not in new_node_properties[new_node_id]:
                                new_node_properties[new_node_id]['sum_' + prop] = node_props[prop]
                                new_node_properties[new_node_id]['count_' + prop] = 1
                            else:
                                new_node_properties[new_node_id]['sum_' + prop] += node_props[prop]
                                new_node_properties[new_node_id]['count_' + prop] += 1
                            # Calculate mean at the end
                        elif agg_func == 'max':
                            current_max = new_node_properties[new_node_id].get(prop, float('-inf'))
                            new_node_properties[new_node_id][prop] = max(current_max, node_props[prop])
                        elif agg_func == 'min':
                            current_min = new_node_properties[new_node_id].get(prop, float('inf'))
                            new_node_properties[new_node_id][prop] = min(current_min, node_props[prop])
                        else:
                            new_node_properties[new_node_id][prop] = node_props[prop]  # Default to last
        # Finalize mean calculations
        for node_id, props in new_node_properties.items():
            for prop in list(props.keys()):
                if prop.startswith('sum_'):
                    base_prop = prop[4:]
                    sum_val = props[prop]
                    count_val = props.get('count_' + base_prop, 1)
                    new_node_properties[node_id][base_prop] = sum_val / count_val if count_val > 0 else 0
                    del new_node_properties[node_id][prop]
                    del new_node_properties[node_id]['count_' + base_prop]
        
        # Handle equivalence class size
        if use_counts:
            for node_id in equivalence_class_dict:
                new_node_properties[node_id]['equivalence_class_size'] = len(equivalence_class_dict[node_id])
        elif return_counts:
            for node_id in new_node_properties:
                if node_id in equivalence_class_dict:
                    new_node_properties[node_id]['equivalence_class_size'] = len(equivalence_class_dict[node_id])
                else:
                    new_node_properties[node_id]['equivalence_class_size'] = 1
        
        # Initialize the collapsed hypergraph
        collapsed_hypergraph = Hypergraph(
            hyperedges={
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in new_hyperedges.items()
            },
            node_properties=new_node_properties,
            hyperedge_properties={
                he_id: copy.deepcopy(he.properties) for he_id, he in new_hyperedges.items()
            },
            name=name if name else f"{self.name}_collapsed_nodes"
        )
        
        if return_equivalence_classes:
            return collapsed_hypergraph, equivalence_class_dict
        else:
            return collapsed_hypergraph

    # Analyzing and Querying the Hypergraph

    def get_toplexes(self, return_hypergraph: bool = False) -> Union[List[Any], 'Hypergraph']:
        """
        Computes a maximal collection of toplexes for the hypergraph.
        A :term:`toplex` is a hyperedge that is not contained in any other hyperedge.

        Parameters
        ----------
        return_hypergraph : bool, optional, default=False
            If True, returns a new Hypergraph consisting only of the toplexes.

        Returns
        -------
        List[Any] or Hypergraph
            - A list of toplex hyperedge IDs.
            - If `return_hypergraph=True`, returns a Hypergraph containing only the toplexes.
        """
        toplexes = []
        hyperedges = list(self.hyperedges.values())

        for he in hyperedges:
            if not any(he.nodes < other_he.nodes for other_he in hyperedges if he.id != other_he.id):
                toplexes.append(he.id)

        if return_hypergraph:
            return self.restrict_to_specific_hyperedges(toplexes, name="Toplexes")
        return toplexes

    def is_node_connected(self, s: int = 1) -> bool:
        """
        Determines if the hypergraph is s-node-connected.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.

        Returns
        -------
        bool
            True if the hypergraph is s-node-connected, False otherwise.
        """
        return self._is_connected(s=s, hyperedges=False)

    def is_hyperedge_connected(self, s: int = 1) -> bool:
        """
        Determines if the hypergraph is s-hyperedge-connected.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.

        Returns
        -------
        bool
            True if the hypergraph is s-hyperedge-connected, False otherwise.
        """
        return self._is_connected(s=s, hyperedges=True)

    def _is_connected(self, s: int = 1, hyperedges: bool = False) -> bool:
        """
        Internal method to determine connectivity based on nodes or hyperedges.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.
        hyperedges : bool, optional, default=False
            If True, checks for s-hyperedge-connectedness. Otherwise, checks for s-node-connectedness.

        Returns
        -------
        bool
            Connectivity status.
        """
        if hyperedges:
            # Create hyperedge connectivity graph: hyperedges are nodes, connect if they share >= s nodes
            hyperedge_graph = nx.Graph()
            hyperedge_ids = list(self.hyperedges.keys())
            hyperedge_graph.add_nodes_from(hyperedge_ids)

            for i, he1 in enumerate(hyperedge_ids):
                nodes1 = self.hyperedges[he1].nodes
                for he2 in hyperedge_ids[i+1:]:
                    nodes2 = self.hyperedges[he2].nodes
                    shared_nodes = nodes1 & nodes2
                    if len(shared_nodes) >= s:
                        hyperedge_graph.add_edge(he1, he2)

            try:
                return nx.is_connected(hyperedge_graph)
            except nx.NetworkXPointlessConcept:
                return False
        else:
            # Create node connectivity graph: nodes are nodes, connect if they share >= s hyperedges
            node_graph = nx.Graph()
            node_ids = list(self.node_properties.keys())
            node_graph.add_nodes_from(node_ids)

            for i, node1 in enumerate(node_ids):
                hyperedges1 = {he.id for he in self.hyperedges.values() if node1 in he.nodes}
                for node2 in node_ids[i+1:]:
                    hyperedges2 = {he.id for he in self.hyperedges.values() if node2 in he.nodes}
                    shared_hyperedges = hyperedges1 & hyperedges2
                    if len(shared_hyperedges) >= s:
                        node_graph.add_edge(node1, node2)

            try:
                return nx.is_connected(node_graph)
            except nx.NetworkXPointlessConcept:
                return False

    def get_node_connected_components(
        self, s: int = 1, return_singletons: bool = False
    ) -> Iterator[Set[Any]]:
        """
        Yields the s-node-connected components of the hypergraph.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.
        return_singletons : bool, optional, default=False
            If True, includes singleton components. Otherwise, excludes them.

        Yields
        ------
        Set[Any]
            Sets of node IDs representing each connected component.
        """
        return self.s_connected_components(s=s, hyperedges=False, return_singletons=return_singletons)

    def get_hyperedge_connected_components(
        self, s: int = 1, return_singletons: bool = False
    ) -> Iterator[Set[Any]]:
        """
        Yields the s-hyperedge-connected components of the hypergraph.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.
        return_singletons : bool, optional, default=False
            If True, includes singleton components. Otherwise, excludes them.

        Yields
        ------
        Set[Any]
            Sets of hyperedge IDs representing each connected component.
        """
        return self.s_connected_components(s=s, hyperedges=True, return_singletons=return_singletons)

    def get_node_connected_subgraphs(
        self, s: int = 1, return_singletons: bool = False, name: Optional[str] = None
    ) -> Iterator['Hypergraph']:
        """
        Yields subgraphs corresponding to each s-node-connected component.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.
        return_singletons : bool, optional, default=False
            If True, includes singleton components. Otherwise, excludes them.
        name : Optional[str], default=None
            Base name for the subgraphs. Each subgraph will have a unique name appended.

        Yields
        ------
        Hypergraph
            Subgraphs representing each connected component.
        """
        return self.s_component_subgraphs(
            s=s,
            hyperedges=False,
            return_singletons=return_singletons,
            name=name
        )

    def get_hyperedge_connected_subgraphs(
        self, s: int = 1, return_singletons: bool = False, name: Optional[str] = None
    ) -> Iterator['Hypergraph']:
        """
        Yields subgraphs corresponding to each s-hyperedge-connected component.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.
        return_singletons : bool, optional, default=False
            If True, includes singleton components. Otherwise, excludes them.
        name : Optional[str], default=None
            Base name for the subgraphs. Each subgraph will have a unique name appended.

        Yields
        ------
        Hypergraph
            Subgraphs representing each connected component.
        """
        return self.s_component_subgraphs(
            s=s,
            hyperedges=True,
            return_singletons=return_singletons,
            name=name
        )

    def get_singleton_hyperedges(self) -> List[Any]:
        """
        Returns a list of singleton hyperedges.
        A singleton hyperedge is a hyperedge of size 1 where its sole node has degree 1.

        Returns
        -------
        List[Any]
            A list of singleton hyperedge IDs.
        """
        singletons = []
        for he in self.hyperedges.values():
            if len(he.nodes) == 1:
                node = next(iter(he.nodes))
                node_degree = sum(1 for hyperedge in self.hyperedges.values() if node in hyperedge.nodes)
                if node_degree == 1:
                    singletons.append(he.id)
        return singletons

    def remove_singleton_hyperedges(self, name: Optional[str] = None) -> 'Hypergraph':
        """
        Constructs a clone of the hypergraph with singleton hyperedges removed.
        """
        singletons = self.get_singleton_hyperedges()
        if not singletons:
            return self.copy(name=name)

        new_hypergraph = self.remove_hyperedges(singletons, inplace=False)
        new_hypergraph.name = name if name else f"{self.name}_no_singleton_hyperedges"
        return new_hypergraph

    def s_connected_components(
        self, 
        s: int = 1, 
        hyperedges: bool = True, 
        return_singletons: bool = False
    ) -> Iterator[Set[Any]]:
        """
        Yields the s-hyperedge-connected or s-node-connected components of the hypergraph.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.
        hyperedges : bool, optional, default=True
            If True, yields s-hyperedge-connected components. Otherwise, yields s-node-connected components.
        return_singletons : bool, optional, default=False
            If True, includes singleton components. Otherwise, excludes them.

        Yields
        ------
        Set[Any]
            Sets of hyperedge IDs or node IDs representing each connected component.
        """
        if hyperedges:
            # s-hyperedge-connected: hyperedges are connected if they share at least s nodes
            hyperedge_graph = nx.Graph()
            hyperedge_ids = list(self.hyperedges.keys())
            hyperedge_graph.add_nodes_from(hyperedge_ids)

            for i, he1 in enumerate(hyperedge_ids):
                nodes1 = self.hyperedges[he1].nodes
                for he2 in hyperedge_ids[i + 1:]:
                    nodes2 = self.hyperedges[he2].nodes
                    shared_nodes = nodes1 & nodes2
                    if len(shared_nodes) >= s:
                        hyperedge_graph.add_edge(he1, he2)

            components = nx.connected_components(hyperedge_graph)
            for component in components:
                if not return_singletons and len(component) == 1:
                    continue
                yield component
        else:
            # s-node-connected: nodes are connected if they share at least s hyperedges
            node_graph = nx.Graph()
            node_ids = list(self.node_properties.keys())
            node_graph.add_nodes_from(node_ids)

            for i, node1 in enumerate(node_ids):
                hyperedges1 = {he.id for he in self.hyperedges.values() if node1 in he.nodes}
                for node2 in node_ids[i + 1:]:
                    hyperedges2 = {he.id for he in self.hyperedges.values() if node2 in he.nodes}
                    shared_hyperedges = hyperedges1 & hyperedges2
                    if len(shared_hyperedges) >= s:
                        node_graph.add_edge(node1, node2)

            components = nx.connected_components(node_graph)
            for component in components:
                if not return_singletons and len(component) == 1:
                    continue
                yield component

    def s_component_subgraphs(
        self,
        s: int = 1,
        hyperedges: bool = True,
        return_singletons: bool = False,
        name: Optional[str] = None
    ) -> Iterator['Hypergraph']:
        """
        Yields subgraphs corresponding to each s-hyperedge-connected or s-node-connected component.

        Parameters
        ----------
        s : int, optional, default=1
            The connectivity level to check.
        hyperedges : bool, optional, default=True
            If True, yields subgraphs of s-hyperedge-connected components. Otherwise, yields subgraphs of s-node-connected components.
        return_singletons : bool, optional, default=False
            If True, includes singleton components. Otherwise, excludes them.
        name : Optional[str], default=None
            Base name for the subgraphs. Each subgraph will have a unique name appended.

        Yields
        ------
        Hypergraph
            Subgraphs representing each connected component.
        """
        for idx, component in enumerate(
            self.s_connected_components(s=s, hyperedges=hyperedges, return_singletons=return_singletons)
        ):
            if hyperedges:
                yield self.restrict_to_specific_hyperedges(
                    hyperedges_to_retain=component, 
                    name=f"{name or self.name}_component_{idx}"
                )
            else:
                yield self.restrict_to_specific_nodes(
                    nodes_to_retain=component, 
                    name=f"{name or self.name}_component_{idx}"
                )

    def compute_node_diameters(self, s: int = 1) -> Tuple[int, List[int], List[Set[Any]]]:
        """
        Returns the node diameters of the connected components in the hypergraph.

        Parameters
        ----------
        s : int, optional, default=1
            The number of shared hyperedges required for nodes to be considered adjacent.

        Returns
        -------
        Tuple[int, List[int], List[Set[Any]]]
            - Maximum diameter among all connected components.
            - List of diameters for each s-node connected component.
            - List of sets, each containing node IDs in an s-node connected component.
        
        Raises
        ------
        HypergraphError
            If the hypergraph is not s-connected or has no nodes.
        """
        A, node_id_map = self.adjacency_matrix(s=s, index=True)
        if A is None or A.shape[0] == 0:
            raise HypergraphError("The hypergraph has no nodes to compute diameters.")
        
        graph = nx.from_scipy_sparse_array(A)

        if not nx.is_connected(graph):
            raise HypergraphError(f"Hypergraph is not s-node-connected. s={s}")

        diams = []
        comps = []
        for component in nx.connected_components(graph):
            subgraph = graph.subgraph(component)
            if len(subgraph) == 1:
                diamc = 0  # Diameter of a single node is 0
            else:
                try:
                    diamc = nx.diameter(subgraph)
                except nx.NetworkXError:
                    diamc = float('inf')  # Infinite diameter if the subgraph is not connected
            diams.append(diamc)
            component_nodes = {node_id_map[node] for node in component}
            comps.append(component_nodes)

        if not diams:
            raise HypergraphError("No connected components found to compute diameters.")

        max_diam = max(diams)
        return max_diam, diams, comps

    def compute_hyperedge_diameters(self, s: int = 1) -> Tuple[int, List[int], List[Set[Any]]]:
        """
        Returns the hyperedge diameters of the s-hyperedge-connected component subgraphs in the hypergraph.

        Parameters
        ----------
        s : int, optional, default=1
            The number of shared nodes required for hyperedges to be considered adjacent.

        Returns
        -------
        Tuple[int, List[int], List[Set[Any]]]
            - Maximum diameter among all s-hyperedge-connected components.
            - List of diameters for each s-hyperedge connected component.
            - List of sets, each containing hyperedge IDs in an s-hyperedge connected component.

        Raises
        ------
        HypergraphError
            If the hypergraph is not s-hyperedge-connected or has no hyperedges.
        """
        A, he_id_map = self.hyperedge_adjacency_matrix(s=s, index=True)
        if A is None or A.shape[0] == 0:
            raise HypergraphError("The hypergraph has no hyperedges to compute diameters.")
        
        graph = nx.from_scipy_sparse_array(A)

        if not nx.is_connected(graph):
            raise HypergraphError(f"Hypergraph is not s-hyperedge-connected. s={s}")

        diams = []
        comps = []
        for component in nx.connected_components(graph):
            subgraph = graph.subgraph(component)
            if len(subgraph) == 1:
                diamc = 0  # Diameter of a single hyperedge is 0
            else:
                try:
                    diamc = nx.diameter(subgraph)
                except nx.NetworkXError:
                    diamc = float('inf')  # Infinite diameter if the subgraph is not connected
            diams.append(diamc)
            component_hyperedges = {he_id_map[he] for he in component}
            comps.append(component_hyperedges)

        if not diams:
            raise HypergraphError("No connected components found to compute hyperedge diameters.")

        max_diam = max(diams)
        return max_diam, diams, comps

    def compute_node_diameter(self, s: int = 1) -> int:
        """
        Returns the diameter of the hypergraph based on s-node connectivity.

        Parameters
        ----------
        s : int, optional, default=1
            The number of shared hyperedges required for nodes to be considered adjacent.

        Returns
        -------
        int
            The diameter of the hypergraph.

        Raises
        ------
        HypergraphError
            If the hypergraph is not s-node-connected or has no nodes.
        """
        A, _ = self.adjacency_matrix(s=s, index=True)
        if A is None or A.shape[0] == 0:
            raise HypergraphError("The hypergraph has no nodes to compute diameter.")
        
        graph = nx.from_scipy_sparse_array(A)
        if not nx.is_connected(graph):
            raise HypergraphError(f"Hypergraph is not s-node-connected. s={s}")

        try:
            return nx.diameter(graph)
        except nx.NetworkXError as e:
            raise HypergraphError(f"Could not compute diameter: {e}")

    def compute_hyperedge_diameter(self, s: int = 1) -> int:
        """
        Returns the diameter of the hypergraph based on s-hyperedge connectivity.

        Parameters
        ----------
        s : int, optional, default=1
            The number of shared nodes required for hyperedges to be considered adjacent.

        Returns
        -------
        int
            The diameter of the hypergraph based on hyperedge connectivity.

        Raises
        ------
        HypergraphError
            If the hypergraph is not s-hyperedge-connected or has no hyperedges.
        """
        A, _ = self.hyperedge_adjacency_matrix(s=s, index=True)
        if A is None or A.shape[0] == 0:
            raise HypergraphError("The hypergraph has no hyperedges to compute diameter.")
        
        graph = nx.from_scipy_sparse_array(A)
        if not nx.is_connected(graph):
            raise HypergraphError(f"Hypergraph is not s-hyperedge-connected. s={s}")

        try:
            return nx.diameter(graph)
        except nx.NetworkXError as e:
            raise HypergraphError(f"Could not compute hyperedge diameter: {e}")

    def get_node_distance(self, source: Any, target: Any, s: int = 1) -> Union[int, float]:
        """
        Returns the shortest s-walk distance between two nodes in the hypergraph.

        Parameters
        ----------
        source : Any
            A node identifier in the hypergraph.
        target : Any
            A node identifier in the hypergraph.
        s : int, optional, default=1
            The number of shared hyperedges required for nodes to be considered adjacent.

        Returns
        -------
        Union[int, float]
            The shortest s-walk distance between the source and target nodes.
            Returns `float('inf')` if no path exists.

        Raises
        ------
        HypergraphError
            If either the source or target node does not exist in the hypergraph.
        """
        if source not in self.node_properties:
            raise HypergraphError(f"Source node '{source}' does not exist in the hypergraph.")
        if target not in self.node_properties:
            raise HypergraphError(f"Target node '{target}' does not exist in the hypergraph.")

        A, node_id_map = self.adjacency_matrix(s=s, index=True)
        if A is None:
            raise HypergraphError("Adjacency matrix could not be generated.")

        graph = nx.from_scipy_sparse_array(A)

        try:
            distance = nx.shortest_path_length(graph, source=source, target=target)
            return distance
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            warnings.warn(f"No s-walk path between '{source}' and '{target}'. Returning infinity.")
            return float('inf')

    def get_hyperedge_distance(self, source: Any, target: Any, s: int = 1) -> Union[int, float]:
        """
        Returns the shortest s-walk distance between two hyperedges in the hypergraph.

        Parameters
        ----------
        source : Any
            A hyperedge identifier in the hypergraph.
        target : Any
            A hyperedge identifier in the hypergraph.
        s : int, optional, default=1
            The number of shared nodes required for hyperedges to be considered adjacent.

        Returns
        -------
        Union[int, float]
            The shortest s-walk distance between the source and target hyperedges.
            Returns `float('inf')` if no path exists.

        Raises
        ------
        HypergraphError
            If either the source or target hyperedge does not exist in the hypergraph.
        """
        if source not in self.hyperedges:
            raise HypergraphError(f"Source hyperedge '{source}' does not exist in the hypergraph.")
        if target not in self.hyperedges:
            raise HypergraphError(f"Target hyperedge '{target}' does not exist in the hypergraph.")

        A, he_id_map = self.hyperedge_adjacency_matrix(s=s, index=True)
        if A is None:
            raise HypergraphError("Hyperedge adjacency matrix could not be generated.")

        graph = nx.from_scipy_sparse_array(A)

        try:
            distance = nx.shortest_path_length(graph, source=source, target=target)
            return distance
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            warnings.warn(f"No s-walk path between hyperedges '{source}' and '{target}'. Returning infinity.")
            return float('inf')

    # Advanced Operations and Transformations

    def union(self, other: 'Hypergraph', inplace: bool = False, name: Optional[str] = None) -> 'Hypergraph':
        """
        Returns the union of the current hypergraph with another hypergraph.
        The union combines all nodes and hyperedges from both hypergraphs.

        Parameters
        ----------
        other : Hypergraph
            The hypergraph to union with.
        inplace : bool, optional, default=False
            If True, modifies the current hypergraph. Otherwise, returns a new Hypergraph instance.
        name : Optional[str], default=None
            The name for the resulting hypergraph. If None, defaults to 'Union_of_{self.name}_{other.name}'.

        Returns
        -------
        Hypergraph
            The resulting union hypergraph.

        Raises
        ------
        TypeError
            If `other` is not an instance of Hypergraph.
        """
        if not isinstance(other, Hypergraph):
            raise TypeError("The `other` parameter must be an instance of Hypergraph.")

        if inplace:
            # Add nodes from other
            for node_id, props in other.node_properties.items():
                if node_id not in self.node_properties:
                    self.add_node(node_id, properties=props, inplace=True)
                else:
                    # Optionally, merge properties
                    self.node_properties[node_id].update(props)
                    self.graph.nodes[node_id].update(props)
            
            # Add hyperedges from other
            for he_id, hyperedge in other.hyperedges.items():
                if he_id not in self.hyperedges:
                    self.add_hyperedge(he_id, hyperedge.nodes, properties=hyperedge.properties)
                else:
                    # Optionally, merge properties and nodes
                    self.hyperedges[he_id].nodes.update(hyperedge.nodes)
                    self.hyperedge_properties[he_id].update(hyperedge.properties)
                    for node in hyperedge.nodes:
                        if node not in self.graph:
                            self.add_node(node)
                        self.graph.add_edge(he_id, node)
            if name:
                self.name = name
            return self
        else:
            # Create a new Hypergraph instance
            new_hyperedges = copy.deepcopy(self.hyperedges)
            new_node_properties = copy.deepcopy(self.node_properties)
            new_hyperedge_properties = copy.deepcopy(self.hyperedge_properties)
            new_graph = copy.deepcopy(self.graph)
            new_bipartite_nodes = copy.deepcopy(self.bipartite_nodes)
            new_name = name if name else f"Union_of_{self.name}_{other.name}"

            # Add nodes from other
            for node_id, props in other.node_properties.items():
                if node_id not in new_node_properties:
                    new_node_properties[node_id] = copy.deepcopy(props)
                    new_graph.add_node(node_id, bipartite='node', **props)
            
            # Add hyperedges from other
            for he_id, hyperedge in other.hyperedges.items():
                if he_id not in new_hyperedges:
                    new_hyperedges[he_id] = copy.deepcopy(hyperedge)
                    new_hyperedge_properties[he_id] = copy.deepcopy(other.hyperedge_properties[he_id])
                    new_graph.add_node(he_id, bipartite='hyperedge', **new_hyperedge_properties[he_id])
                    new_bipartite_nodes.add(he_id)
                    for node in hyperedge.nodes:
                        new_graph.add_edge(he_id, node)
                else:
                    # Merge nodes and properties
                    new_hyperedges[he_id].nodes.update(hyperedge.nodes)
                    new_hyperedge_properties[he_id].update(other.hyperedge_properties[he_id])
                    for node in hyperedge.nodes:
                        new_graph.add_edge(he_id, node)
            
            # Construct the new Hypergraph
            return Hypergraph(
                hyperedges={
                    he_id: {
                        'nodes': list(he.nodes),
                        'properties': he.properties.copy()
                    } for he_id, he in new_hyperedges.items()
                },
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=new_name
            )

    def intersection(self, other: 'Hypergraph', inplace: bool = False, name: Optional[str] = None) -> 'Hypergraph':
        """
        Returns the intersection of the current hypergraph with another hypergraph.
        The intersection includes only nodes and hyperedges present in both hypergraphs.

        Parameters
        ----------
        other : Hypergraph
            The hypergraph to intersect with.
        inplace : bool, optional, default=False
            If True, modifies the current hypergraph to keep only the intersecting elements.
            Otherwise, returns a new Hypergraph instance.
        name : Optional[str], default=None
            The name for the resulting hypergraph. If None, defaults to 'Intersection_of_{self.name}_{other.name}'.

        Returns
        -------
        Hypergraph
            The resulting intersection hypergraph.

        Raises
        ------
        TypeError
            If `other` is not an instance of Hypergraph.
        """
        if not isinstance(other, Hypergraph):
            raise TypeError("The `other` parameter must be an instance of Hypergraph.")

        intersect_nodes = set(self.node_properties.keys()) & set(other.node_properties.keys())
        intersect_hyperedges = set(self.hyperedges.keys()) & set(other.hyperedges.keys())

        if inplace:
            # Remove non-intersecting nodes and hyperedges
            nodes_to_remove = set(self.node_properties.keys()) - intersect_nodes
            hyperedges_to_remove = set(self.hyperedges.keys()) - intersect_hyperedges
            self.remove_nodes_from(nodes_to_remove, inplace=True)
            self.remove_hyperedges(hyperedges_to_remove, inplace=True)
            return self
        else:
            # Create a new Hypergraph instance
            new_hyperedges = {}
            new_node_properties = {node_id: copy.deepcopy(self.node_properties[node_id]) for node_id in intersect_nodes}
            new_hyperedge_properties = {}
            new_graph = nx.Graph()
            new_bipartite_nodes = set()

            for he_id in intersect_hyperedges:
                he_self = self.hyperedges[he_id]
                he_other = other.hyperedges[he_id]
                # Intersection hyperedges have the same nodes and merged properties
                new_nodes = set(he_self.nodes) & set(he_other.nodes)
                if not new_nodes:
                    continue  # Skip hyperedges with no common nodes
                new_hyperedges[he_id] = HyperEdge(id=he_id, nodes=new_nodes, properties={})
                # Merge properties (could define specific rules)
                new_hyperedge_properties[he_id] = {**self.hyperedge_properties.get(he_id, {}), 
                                                   **other.hyperedge_properties.get(he_id, {})}
                new_graph.add_node(he_id, bipartite='hyperedge', **new_hyperedge_properties[he_id])
                new_bipartite_nodes.add(he_id)
                for node in new_nodes:
                    new_graph.add_edge(he_id, node)
            
            return Hypergraph(
                hyperedges={
                    he_id: {
                        'nodes': list(he.nodes),
                        'properties': he.properties.copy()
                    } for he_id, he in new_hyperedges.items()
                },
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=name if name else f"Intersection_of_{self.name}_{other.name}"
            )

    def difference(self, other: 'Hypergraph', inplace: bool = False, name: Optional[str] = None) -> 'Hypergraph':
        """
        Returns the difference of the current hypergraph with another hypergraph.
        The difference includes nodes and hyperedges present in the current hypergraph but not in the other.

        Parameters
        ----------
        other : Hypergraph
            The hypergraph to subtract.
        inplace : bool, optional, default=False
            If True, modifies the current hypergraph by removing elements found in `other`.
            Otherwise, returns a new Hypergraph instance.
        name : Optional[str], default=None
            The name for the resulting hypergraph. If None, defaults to 'Difference_of_{self.name}_{other.name}'.

        Returns
        -------
        Hypergraph
            The resulting difference hypergraph.

        Raises
        ------
        TypeError
            If `other` is not an instance of Hypergraph.
        """
        if not isinstance(other, Hypergraph):
            raise TypeError("The `other` parameter must be an instance of Hypergraph.")

        if inplace:
            # Remove hyperedges present in other
            hyperedges_to_remove = set(self.hyperedges.keys()) & set(other.hyperedges.keys())
            self.remove_hyperedges(hyperedges_to_remove, inplace=True)
            # Remove nodes present in other
            nodes_to_remove = set(self.node_properties.keys()) & set(other.node_properties.keys())
            self.remove_nodes_from(nodes_to_remove, inplace=True)
            return self
        else:
            # Create a new Hypergraph instance
            new_hyperedges = {he_id: copy.deepcopy(he) for he_id, he in self.hyperedges.items() if he_id not in other.hyperedges}
            new_hyperedge_properties = {he_id: copy.deepcopy(props) for he_id, props in self.hyperedge_properties.items() if he_id not in other.hyperedges}
            new_node_properties = {node_id: copy.deepcopy(props) for node_id, props in self.node_properties.items() if node_id not in other.node_properties}
            
            # Reconstruct graph
            new_graph = nx.Graph()
            new_bipartite_nodes = set()
            for he_id, hyperedge in new_hyperedges.items():
                new_graph.add_node(he_id, bipartite='hyperedge', **new_hyperedge_properties[he_id])
                new_bipartite_nodes.add(he_id)
                for node in hyperedge.nodes:
                    if node in new_node_properties:
                        new_graph.add_edge(he_id, node)
            
            return Hypergraph(
                hyperedges={
                    he_id: {
                        'nodes': list(he.nodes),
                        'properties': he.properties.copy()
                    } for he_id, he in new_hyperedges.items()
                },
                node_properties=new_node_properties,
                hyperedge_properties=new_hyperedge_properties,
                name=name if name else f"Difference_of_{self.name}_{other.name}"
            )

    def symmetric_difference(self, other: 'Hypergraph', inplace: bool = False, name: Optional[str] = None) -> 'Hypergraph':
        """
        Returns the symmetric difference of the current hypergraph with another hypergraph.
        The symmetric difference includes elements present in either hypergraph but not in both.

        Parameters
        ----------
        other : Hypergraph
            The hypergraph to symmetric difference with.
        inplace : bool, optional, default=False
            If True, modifies the current hypergraph to keep only the symmetric difference elements.
            Otherwise, returns a new Hypergraph instance.
        name : Optional[str], default=None
            The name for the resulting hypergraph. If None, defaults to 'SymmetricDifference_of_{self.name}_{other.name}'.

        Returns
        -------
        Hypergraph
            The resulting symmetric difference hypergraph.

        Raises
        ------
        TypeError
            If `other` is not an instance of Hypergraph.
        """
        if not isinstance(other, Hypergraph):
            raise TypeError("The `other` parameter must be an instance of Hypergraph.")

        if inplace:
            # Hyperedges symmetric difference
            hyperedges_to_add = set(other.hyperedges.keys()) - set(self.hyperedges.keys())
            hyperedges_to_remove = set(self.hyperedges.keys()) & set(other.hyperedges.keys())
            self.remove_hyperedges(hyperedges_to_remove, inplace=True)
            for he_id in hyperedges_to_add:
                hyperedge = other.hyperedges[he_id]
                self.add_hyperedge(he_id, hyperedge.nodes, properties=hyperedge.properties)
            
            # Nodes symmetric difference
            nodes_to_add = set(other.node_properties.keys()) - set(self.node_properties.keys())
            nodes_to_remove = set(self.node_properties.keys()) & set(other.node_properties.keys())
            self.remove_nodes_from(nodes_to_remove, inplace=True)
            for node_id in nodes_to_add:
                props = other.node_properties[node_id]
                self.add_node(node_id, properties=props, inplace=True)
            
            if name:
                self.name = name
            return self
        else:
            # Create a new Hypergraph instance
            union_hg = self.union(other)
            intersection_hg = self.intersection(other)
            return union_hg.difference(intersection_hg, name=name if name else f"SymmetricDifference_of_{self.name}_{other.name}")
    
    def transpose(self, name: Optional[str] = None) -> 'Hypergraph':
        """
        Transposes the hypergraph by swapping the roles of nodes and hyperedges.
        The resulting hypergraph has hyperedges corresponding to the original nodes and vice versa.

        Parameters
        ----------
        name : Optional[str], default=None
            The name assigned to the transposed hypergraph. If None, defaults to the original name suffixed with '_transposed'.

        Returns
        -------
        Hypergraph
            The transposed hypergraph.
        """
        transposed_hyperedges = {node_id: HyperEdge(id=node_id, nodes=set(), properties=copy.deepcopy(props))
                                 for node_id, props in self.node_properties.items()}
        transposed_node_properties = {he_id: copy.deepcopy(props) for he_id, props in self.hyperedge_properties.items()}
        
        for he_id, hyperedge in self.hyperedges.items():
            for node in hyperedge.nodes:
                if node in transposed_hyperedges:
                    transposed_hyperedges[node].nodes.add(he_id)
        
        # Construct the transposed hypergraph
        return Hypergraph(
            hyperedges={
                he_id: {
                    'nodes': list(he.nodes),
                    'properties': he.properties.copy()
                } for he_id, he in transposed_hyperedges.items()
            },
            node_properties=transposed_node_properties,
            hyperedge_properties={he_id: he.properties.copy() for he_id, he in transposed_hyperedges.items()},
            name=name if name else f"{self.name}_transposed"
        )

    def to_bipartite_graph(self, keep_data=False, directed=False) -> nx.Graph:
        """
        Creates a bipartite NetworkX graph from the hypergraph.
        The nodes and hyperedges of the hypergraph become nodes in the bipartite graph.
        For every hyperedge in the hypergraph and each node it connects to, there
        is an edge in the bipartite graph.

        Parameters
        ----------
        keep_data : bool, optional, default = False
            If True, includes the node and hyperedge properties in the NetworkX graph.
        directed : bool, optional, default = False
            If True, the edges in the graph are directed with hyperedges as sources and nodes as targets.

        Returns
        -------
        networkx.Graph or networkx.DiGraph
            The bipartite graph representation of the hypergraph.
        """
        # Choose graph type based on directed flag
        B = nx.DiGraph() if directed else nx.Graph()

        if not keep_data:
            # Add nodes with bipartite attributes, where 0 indicates hyperedges and 1 indicates regular nodes
            B.add_nodes_from(self.hyperedges.keys(), bipartite=0)  # hyperedges
            B.add_nodes_from(self.node_properties.keys(), bipartite=1)  # nodes

            # Add edges between hyperedges and nodes based on hyperedges data
            for he_id, hyperedge in self.hyperedges.items():
                for node in hyperedge.nodes:
                    B.add_edge(he_id, node)
        else:
            # Add nodes with properties if keep_data is True
            for node_id, properties in self.node_properties.items():
                B.add_node(node_id, bipartite=1, **properties)

            for he_id, hyperedge in self.hyperedges.items():
                B.add_node(he_id, bipartite=0, **self.hyperedge_properties.get(he_id, {}))
                for node in hyperedge.nodes:
                    # Add edges with optional properties if keep_data is True
                    B.add_edge(he_id, node)

        return B
    
    @classmethod
    def from_bipartite_graph(cls, bipartite_graph: nx.Graph, hyperedge_prefix: str = "HE", node_prefix: str = "N", name: Optional[str] = None) -> 'Hypergraph':
        """
        Constructs a Hypergraph instance from a bipartite graph.

        Parameters
        ----------
        bipartite_graph : nx.Graph
            A bipartite graph where one set of nodes represents hyperedges and the other represents regular nodes.
        hyperedge_prefix : str, optional, default="HE"
            The prefix to identify hyperedge nodes in the bipartite graph.
        node_prefix : str, optional, default="N"
            The prefix to identify regular nodes in the bipartite graph.
        name : Optional[str], default=None
            The name assigned to the new Hypergraph. If None, defaults to 'FromBipartiteGraph'.

        Returns
        -------
        Hypergraph
            The constructed Hypergraph instance.

        Raises
        ------
        ValueError
            If the bipartite graph does not contain two distinct sets of nodes identifiable by the provided prefixes.
        """
        hyperedges = {}
        node_properties = {}
        hyperedge_properties = {}
        name = name if name else "FromBipartiteGraph"

        for node in bipartite_graph.nodes(data=True):
            node_id, attrs = node
            if node_id.startswith(hyperedge_prefix):
                # It's a hyperedge
                hyperedges[node_id] = HyperEdge(id=node_id, nodes=set(), properties=attrs)
                hyperedge_properties[node_id] = copy.deepcopy(attrs)
            elif node_id.startswith(node_prefix):
                # It's a regular node
                node_properties[node_id] = copy.deepcopy(attrs)
            else:
                raise ValueError(f"Node '{node_id}' does not start with either hyperedge_prefix '{hyperedge_prefix}' or node_prefix '{node_prefix}'.")

        # Assign nodes to hyperedges based on edges in bipartite graph
        for he_id in hyperedges:
            connected_nodes = set(bipartite_graph.neighbors(he_id))
            hyperedges[he_id].nodes = connected_nodes

        # Construct hyperedges dict for __init__
        hyperedges_dict = {
            he_id: {
                'nodes': list(he.nodes),
                'properties': he.properties.copy()
            } for he_id, he in hyperedges.items()
        }

        return cls(
            hyperedges=hyperedges_dict,
            node_properties=node_properties,
            hyperedge_properties=hyperedge_properties,
            name=name
        )