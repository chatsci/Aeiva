import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Dict, Optional, Any, Union
from aeiva.action.step import Step
from aeiva.action.status import Status

class Procedure:
    """
    Abstract base class for composite structures like Plan and Skill.
    Contains shared attributes and methods for organizing and managing steps (e.g., tasks, sub-procedures) 
    in a directed acyclic graph (DAG).
    """

    def __init__(self, name: str, steps: List[Union['Procedure', Step]],
                 id: Optional[str] = None, dependent_ids: Optional[List[str]] = None,
                 type: Optional[str] = None, description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 *args, **kwargs):
        self.name = name
        self.steps = steps
        self.id = id
        self.dependent_ids = dependent_ids or []
        self.type = type
        self.description = description
        self.metadata = metadata or {}

        self.graph = nx.DiGraph()
        self.step_map = {step.id: step for step in steps}
        self.status = Status.NOT_EXECUTED

        # Add all steps as nodes in the graph
        for step in steps:
            self.graph.add_node(step)

        # Handle dependencies for steps
        for step in steps:
            for dep_id in step.dependent_ids:
                if dep_id in self.step_map:
                    self.graph.add_edge(self.step_map[dep_id], step)
                else:
                    raise ValueError(f"Dependency {dep_id} not found for step {step.id}.")

    def get_topological_sort(self):
        """
        Returns the steps in topologically sorted order based on the dependency graph.
        Ensures that all prerequisite steps are executed before the dependent ones.
        """
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            raise ValueError("The dependency graph contains cycles, which is not allowed in a procedure.")

    def reset(self) -> None:
        """
        Resets the status of the procedure and all its steps.
        """
        self.status = Status.NOT_EXECUTED
        for step in self.steps:
            step.reset()

    def start(self) -> None:
        """
        Marks the procedure as in progress. Raises an error if it's already in progress or finished.
        """
        if self.status != Status.NOT_EXECUTED:
            raise ValueError(f"{self.type} {self.id} has already been started or finished.")
        self.status = Status.EXECUTING

    def end(self, success: bool) -> None:
        """
        Marks the procedure as completed. Raises an error if it hasn't started yet.
        """
        if self.status != Status.EXECUTING:
            raise ValueError(f"Cannot finish {self.type} that hasn't started.")
        self.status = Status.SUCCESS if success else Status.FAIL

    @property
    def is_successful(self) -> bool:
        return all(step.is_successful for step in self.steps)

    @property
    def is_failed(self) -> bool:
        return any(step.is_failed for step in self.steps)

    @property
    def is_in_progress(self) -> bool:
        return any(step.is_in_progress for step in self.steps)

    @property
    def is_not_started(self) -> bool:
        return all(step.is_not_started for step in self.steps)

    @property
    def is_finished(self) -> bool:
        return all(step.is_finished for step in self.steps)

    def visualize(self, save_path: Optional[str] = None):
        """
        Visualizes the procedure's structure using networkx and matplotlib.
        """
        pos = nx.spring_layout(self.graph)  # Layout for the graph
        labels = {node: f"{node.id} ({node.description}, {node.status})" for node in self.graph.nodes()}

        # Draw the graph with labels
        nx.draw(self.graph, pos, with_labels=True, labels=labels, node_color='lightblue', node_size=2000, font_size=10, font_weight='bold', arrows=True)

        plt.title(f"{self.type} {self.description} Visualization")
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps],
            "id": self.id,
            "dependent_ids": self.dependent_ids,
            "type": self.type,
            "description": self.description,
            "metadata": self.metadata,
            "status": self.status
        }