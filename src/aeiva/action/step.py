"""
Step: The atomic unit for Tasks and Actions.

A Step represents a single unit of work with:
    - Identity (name, id, description)
    - Parameters for execution
    - Dependencies on other steps
    - Status tracking

Inheritance:
    Step
    ├── Task (visualizable, for planning)
    └── Action (executable, with Tool)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from aeiva.action.status import Status


def generate_step_id() -> str:
    """Generate a unique step identifier."""
    return f"step_{uuid.uuid4().hex[:8]}"


@dataclass
class Step:
    """
    Base class for atomic units like Task and Action.

    A Step contains:
        - name: The operation name (tool/function/task name)
        - params: Parameters for execution
        - id: Unique identifier
        - dependent_ids: Steps that must complete before this one
        - description: Human-readable description
        - metadata: Additional context

    Attributes:
        name: The name of the operation to perform
        params: Parameters to pass to the operation
        id: Unique identifier for this step
        dependent_ids: IDs of steps that must complete first
        description: Human-readable description
        metadata: Additional context and configuration
        status: Current execution status
        result: Result of execution (for Actions)
    """

    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=generate_step_id)
    dependent_ids: List[str] = field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: Status = field(default=Status.NOT_EXECUTED)
    result: Any = field(default=None, repr=False)

    @property
    def step_type(self) -> str:
        """Return the type name of this step."""
        return self.__class__.__name__

    def reset(self) -> None:
        """Reset to initial state, ready for re-execution."""
        self.status = Status.NOT_EXECUTED
        self.result = None

    def start(self) -> None:
        """
        Mark execution as started.

        Raises:
            ValueError: If step has already started or finished
        """
        if self.status != Status.NOT_EXECUTED:
            raise ValueError(
                f"{self.step_type} '{self.id}' cannot start: "
                f"current status is {self.status}"
            )
        self.status = Status.EXECUTING

    def succeed(self, result: Any = None) -> None:
        """
        Mark execution as successful.

        Args:
            result: Optional result of the execution

        Raises:
            ValueError: If step is not currently executing
        """
        if self.status != Status.EXECUTING:
            raise ValueError(
                f"{self.step_type} '{self.id}' cannot succeed: "
                f"not currently executing (status: {self.status})"
            )
        self.status = Status.SUCCESS
        self.result = result

    def fail(self, error: Any = None) -> None:
        """
        Mark execution as failed.

        Args:
            error: Optional error information

        Raises:
            ValueError: If step is not currently executing
        """
        if self.status != Status.EXECUTING:
            raise ValueError(
                f"{self.step_type} '{self.id}' cannot fail: "
                f"not currently executing (status: {self.status})"
            )
        self.status = Status.FAIL
        self.result = error

    @property
    def is_successful(self) -> bool:
        """Check if step completed successfully."""
        return self.status == Status.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if step failed."""
        return self.status == Status.FAIL

    @property
    def is_executing(self) -> bool:
        """Check if step is currently executing."""
        return self.status == Status.EXECUTING

    @property
    def is_pending(self) -> bool:
        """Check if step has not started."""
        return self.status == Status.NOT_EXECUTED

    @property
    def is_finished(self) -> bool:
        """Check if step has completed (success or fail)."""
        return self.status.is_terminal

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": self.step_type,
            "name": self.name,
            "params": self.params,
            "id": self.id,
            "dependent_ids": self.dependent_ids,
            "description": self.description,
            "metadata": self.metadata,
            "status": str(self.status),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Step":
        """
        Create a Step from dictionary representation.

        Args:
            data: Dictionary with step data

        Returns:
            New Step instance
        """
        status_str = data.get("status", "not_executed")
        status = Status(status_str) if isinstance(status_str, str) else status_str

        return cls(
            name=data["name"],
            params=data.get("params", {}),
            id=data.get("id", generate_step_id()),
            dependent_ids=data.get("dependent_ids", []),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
            status=status,
        )
