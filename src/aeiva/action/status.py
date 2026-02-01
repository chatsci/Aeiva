"""
Execution status for Steps and Procedures.

The Status enum represents the lifecycle of an executable unit:
    NOT_EXECUTED → EXECUTING → SUCCESS or FAIL

Usage:
    from aeiva.action.status import Status

    step.status = Status.EXECUTING
    if step.status == Status.SUCCESS:
        ...
"""

from enum import Enum, auto


class Status(str, Enum):
    """
    Execution status for Steps and Procedures.

    Inherits from str for JSON serialization compatibility.

    States:
        NOT_EXECUTED: Initial state, ready to execute
        EXECUTING: Currently running
        SUCCESS: Completed successfully
        FAIL: Completed with failure
    """

    NOT_EXECUTED = "not_executed"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAIL = "fail"

    def __str__(self) -> str:
        return self.value

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal (final) state."""
        return self in (Status.SUCCESS, Status.FAIL)

    @property
    def is_active(self) -> bool:
        """Check if execution is currently active."""
        return self == Status.EXECUTING

    @property
    def is_pending(self) -> bool:
        """Check if execution has not started."""
        return self == Status.NOT_EXECUTED
