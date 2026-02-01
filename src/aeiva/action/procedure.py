"""
Procedure: The composite unit for Plans, Skills, and Experiences.

A Procedure organizes Steps in a directed acyclic graph (DAG),
enabling dependency-aware execution or visualization.

Inheritance:
    Procedure
    ├── Plan (composed of Tasks, visualizable)
    ├── Skill (composed of Actions, executable)
    └── Experience (composed of Actions, needs validation)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import uuid

import networkx as nx

from aeiva.action.status import Status
from aeiva.action.step import Step

if TYPE_CHECKING:
    pass


def generate_procedure_id() -> str:
    """Generate a unique procedure identifier."""
    return f"proc_{uuid.uuid4().hex[:8]}"


@dataclass
class Procedure:
    """
    Base class for composite structures like Plan, Skill, and Experience.

    A Procedure contains:
        - name: Identifier for the procedure
        - steps: List of Steps or nested Procedures
        - Dependency graph for execution ordering

    The dependency graph is built from step.dependent_ids, ensuring
    steps execute in the correct order respecting dependencies.

    Attributes:
        name: Identifier for this procedure
        steps: List of Steps or nested Procedures
        id: Unique identifier
        dependent_ids: Procedures that must complete before this one
        description: Human-readable description
        metadata: Additional context and configuration
        status: Current execution status
    """

    name: str
    steps: List[Union["Procedure", Step]] = field(default_factory=list)
    id: str = field(default_factory=generate_procedure_id)
    dependent_ids: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: Status = field(default=Status.NOT_EXECUTED)

    def __post_init__(self):
        """Build the dependency graph after initialization."""
        self._graph: Optional[nx.DiGraph] = None
        self._step_map: Dict[str, Union[Procedure, Step]] = {}
        self._build_graph()

    @property
    def procedure_type(self) -> str:
        """Return the type name of this procedure."""
        return self.__class__.__name__

    def _build_graph(self) -> None:
        """
        Build the dependency graph from steps.

        Creates a directed acyclic graph where edges represent
        dependencies (edge from A to B means A must complete before B).
        """
        self._graph = nx.DiGraph()
        self._step_map = {step.id: step for step in self.steps}

        # Add all steps as nodes
        for step in self.steps:
            self._graph.add_node(step.id, step=step)

        # Add dependency edges
        for step in self.steps:
            for dep_id in step.dependent_ids:
                if dep_id not in self._step_map:
                    raise ValueError(
                        f"Dependency '{dep_id}' not found for step '{step.id}' "
                        f"in procedure '{self.id}'"
                    )
                self._graph.add_edge(dep_id, step.id)

        # Validate no cycles
        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError(
                f"Procedure '{self.id}' contains dependency cycles"
            )

    @property
    def graph(self) -> nx.DiGraph:
        """Access the dependency graph."""
        if self._graph is None:
            self._build_graph()
        return self._graph

    def get_step(self, step_id: str) -> Optional[Union["Procedure", Step]]:
        """Get a step by ID."""
        return self._step_map.get(step_id)

    def topological_order(self) -> List[Union["Procedure", Step]]:
        """
        Get steps in dependency-respecting order.

        Returns:
            Steps ordered so that dependencies come before dependents
        """
        ordered_ids = list(nx.topological_sort(self.graph))
        return [self._step_map[step_id] for step_id in ordered_ids]

    def ready_steps(self) -> List[Union["Procedure", Step]]:
        """
        Get steps that are ready to execute.

        A step is ready if:
            - It has not started yet
            - All its dependencies have completed successfully

        Returns:
            List of steps ready for execution
        """
        ready = []
        for step in self.steps:
            if not step.is_pending:
                continue

            # Check all dependencies are successful
            deps_satisfied = all(
                self._step_map[dep_id].is_successful
                for dep_id in step.dependent_ids
            )
            if deps_satisfied:
                ready.append(step)

        return ready

    def reset(self) -> None:
        """Reset procedure and all steps to initial state."""
        self.status = Status.NOT_EXECUTED
        for step in self.steps:
            step.reset()

    def start(self) -> None:
        """
        Mark procedure execution as started.

        Raises:
            ValueError: If already started or finished
        """
        if self.status != Status.NOT_EXECUTED:
            raise ValueError(
                f"{self.procedure_type} '{self.id}' cannot start: "
                f"current status is {self.status}"
            )
        self.status = Status.EXECUTING

    def succeed(self) -> None:
        """
        Mark procedure as completed successfully.

        Raises:
            ValueError: If not currently executing
        """
        if self.status != Status.EXECUTING:
            raise ValueError(
                f"{self.procedure_type} '{self.id}' cannot succeed: "
                f"not currently executing"
            )
        self.status = Status.SUCCESS

    def fail(self) -> None:
        """
        Mark procedure as failed.

        Raises:
            ValueError: If not currently executing
        """
        if self.status != Status.EXECUTING:
            raise ValueError(
                f"{self.procedure_type} '{self.id}' cannot fail: "
                f"not currently executing"
            )
        self.status = Status.FAIL

    @property
    def is_successful(self) -> bool:
        """Check if all steps completed successfully."""
        return all(step.is_successful for step in self.steps)

    @property
    def is_failed(self) -> bool:
        """Check if any step failed."""
        return any(step.is_failed for step in self.steps)

    @property
    def is_executing(self) -> bool:
        """Check if any step is currently executing."""
        return self.status == Status.EXECUTING

    @property
    def is_pending(self) -> bool:
        """Check if procedure has not started."""
        return self.status == Status.NOT_EXECUTED

    @property
    def is_finished(self) -> bool:
        """Check if all steps have completed."""
        return all(step.is_finished for step in self.steps)

    @property
    def progress(self) -> float:
        """
        Get execution progress as a fraction.

        Returns:
            Float between 0.0 and 1.0
        """
        if not self.steps:
            return 1.0
        finished = sum(1 for step in self.steps if step.is_finished)
        return finished / len(self.steps)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": self.procedure_type,
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps],
            "id": self.id,
            "dependent_ids": self.dependent_ids,
            "description": self.description,
            "metadata": self.metadata,
            "status": str(self.status),
        }

    def visualize_text(self) -> str:
        """
        Generate a text visualization of the procedure structure.

        Returns:
            Multi-line string showing procedure hierarchy
        """
        lines = [f"{self.procedure_type}: {self.name} ({self.id})"]
        lines.append(f"Status: {self.status}")
        lines.append(f"Progress: {self.progress:.0%}")
        lines.append("Steps:")

        for step in self.topological_order():
            status_icon = {
                Status.NOT_EXECUTED: "○",
                Status.EXECUTING: "◐",
                Status.SUCCESS: "●",
                Status.FAIL: "✗",
            }.get(step.status, "?")

            deps = f" (after: {', '.join(step.dependent_ids)})" if step.dependent_ids else ""
            lines.append(f"  {status_icon} {step.name} [{step.id}]{deps}")

        return "\n".join(lines)
