from typing import List, Dict, Optional, Any
from aeiva.action.status import Status

class Step:
    """
    Abstract base class for atomic units like Task and Action.
    Contains shared attributes and methods for managing their execution and dependencies.
    """

    def __init__(self, name: str, params: Dict[str, Any] = None,
                 id: Optional[str] = None, dependent_ids: Optional[List[str]] = None, 
                 type: Optional[str] = None, description: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 *args, **kwargs):
        self.name = name  # The name of the step. It can be a task/action/tool/api/function name
        self.params = params  # The parameters for this step. it can be a task/action/tool/api/function's params
        self.id = id  # Unique identifier for the step
        self.dependent_ids = dependent_ids or []  # List of IDs of steps that must be completed before this one
        self.type = type  # The type of this step, e.g., task or action
        self.description = description  # A description for this step
        self.metadata = metadata or {}  # Optional metadata (e.g., id, type, description, priority, etc.)
        self.status = Status.NOT_EXECUTED  # Initial status

    def reset(self) -> None:
        """
        Resets the step status, making it ready for re-execution.
        """
        self.status = Status.NOT_EXECUTED

    def start(self) -> None:
        """
        Marks the step as in progress. Raises an error if the step is already started or finished.
        """
        if self.status != Status.NOT_EXECUTED:
            raise ValueError(f"{self.type} {self.description} {self.id} has already been started or finished.")
        self.status = Status.EXECUTING

    def end(self, success: bool) -> None:
        """
        Marks the step as finished and indicates whether it was successful.
        Can only be called if the step is in progress.
        """
        if self.status != Status.EXECUTING:
            raise ValueError(f"Cannot finish a {self.type} that hasn't started.")
        self.status = Status.SUCCESS if success else Status.FAIL

    @property
    def is_successful(self) -> bool:
        """
        Returns True if the step was completed successfully.
        """
        return self.status == Status.SUCCESS

    @property
    def is_failed(self) -> bool:
        """
        Returns True if the step has finished but failed.
        """
        return self.status == Status.FAIL

    @property
    def is_in_progress(self) -> bool:
        """
        Returns True if the step is in progress (executing but not finished).
        """
        return self.status == Status.EXECUTING

    @property
    def is_not_started(self) -> bool:
        """
        Returns True if the step has not started yet.
        """
        return self.status == Status.NOT_EXECUTED

    @property
    def is_finished(self) -> bool:
        """
        Returns True if the step has finished execution, either successfully or failed.
        """
        return self.status == Status.SUCCESS or self.status == Status.FAIL

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the step into a dictionary representation.
        """
        return {
            "name": self.name,
            "params": self.params,
            "id": self.id,
            "dependent_ids": self.dependent_ids,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "metadata": self.metadata
        }