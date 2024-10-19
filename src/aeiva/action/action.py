# File: actions/action.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Action(ABC):
    """
    Abstract base class for actions that an agent can perform.
    """
    def __init__(self, name: str, parameters: Optional[Dict[str, Any]] = None):
        self.name = name
        self.parameters = parameters or {}

    @abstractmethod
    def execute(self) -> Any:
        """
        Execute the action.

        Returns:
            Any: The result of the action execution.
        """
        pass