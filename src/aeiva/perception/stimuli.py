import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Dict, Optional, Union, Any
from aeiva.perception.sensation import Signal

class Stimuli:
    """
    Represents a structured composition of signals, where each node can be a Signal or a sub-Stimuli.
    The graph allows flexible, directed relationships between nodes, and the graph can contain cycles.
    """

    def __init__(self, 
                 signals: List[Union[Signal, 'Stimuli']],
                 id: Optional[str] = None,
                 name: Optional[str] = None,
                 type: Optional[str] = None,
                 modularity: Optional[str] = None,
                 timestamp: Optional[str] = None,
                 dependencies: Optional[Dict[str, Dict[str, Any]]] = None,
                 description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initializes the Stimuli object by organizing signals or sub-stimuli in a graph structure.
        """
        self.signals = signals or []  # Default to an empty list if no signals provided
        self.id = id
        self.name = name
        self.type = type
        self.modularity = modularity
        self.timestamp = timestamp
        self.description = description
        self.metadata = metadata or {}
        self.dependencies = dependencies or {}

        # Graph to represent the structure of signals and their relationships
        self.graph = nx.DiGraph()

        # Add all signals and sub-stimuli as nodes in the graph
        for signal in signals:
            self.graph.add_node(signal)

        # Handle dependencies for signals or sub-stimuli
        for signal in signals:
            if signal.id in self.dependencies:
                for dep_id, edge_attr in self.dependencies[signal.id].items():
                    dep_node = next((s for s in signals if s.id == dep_id), None)
                    if dep_node and (isinstance(dep_node, Signal) or isinstance(dep_node, Stimuli)):
                        self.graph.add_edge(dep_node, signal, **edge_attr)
                    else:
                        raise ValueError(f"Dependency {dep_id} not found or is not valid for signal or stimuli {signal.id}.")

    def traverse(self, method: str = 'dfs') -> List[Union[Signal, 'Stimuli']]:
        """
        Traverses the graph using the specified method ('dfs' or 'bfs').

        Args:
            method (str): The traversal method to use, either 'dfs' (Depth-First Search) or 'bfs' (Breadth-First Search).

        Returns:
            List[Union[Signal, 'Stimuli']]: A list of signals or sub-stimuli in the order they were visited.
        """
        if not self.graph.nodes:
            return []

        if method == 'dfs':
            return list(nx.dfs_postorder_nodes(self.graph))
        elif method == 'bfs':
            return list(nx.bfs_tree(self.graph, list(self.graph.nodes)[0]))  # BFS starting from an arbitrary node
        else:
            raise ValueError(f"Unknown traversal method: {method}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the stimuli into a dictionary representation, including its signals and their relationships.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "modularity": self.modularity,
            "timestamp": self.timestamp,
            "description": self.description,
            "metadata": self.metadata,
            "signals": [signal.to_dict() if isinstance(signal, Signal) else signal.to_dict() for signal in self.signals],
            "dependencies": self.dependencies
        }

    def visualize(self, save_path: Optional[str] = None):
        """
        Visualizes the procedure's structure using networkx and matplotlib.
        """
        pos = nx.spring_layout(self.graph)  # Layout for the graph
        labels = {node: f"{node.id} ({node.type})" if isinstance(node, Signal) else f"{node.id} (Stimuli)"
                  for node in self.graph.nodes()}

        # Draw the graph with labels
        nx.draw(self.graph, pos, with_labels=True, labels=labels, node_color='lightblue', node_size=2000, font_size=10, font_weight='bold', arrows=True)

        plt.title(f"{self.type} {self.description} Visualization")
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
