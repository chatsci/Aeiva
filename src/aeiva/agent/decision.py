from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Decision(ABC):
    """
    Abstract base class for decisions. This represents a choice made by the agent, based on its thoughts.
    """
    def __init__(self, *args, **kwargs):
        self.action_plan = self.make_decision(*args, **kwargs)

    @property
    def action_plan(self) -> Dict[str, Any]:
        return self._action_plan

    @action_plan.setter
    def action_plan(self, value: Dict[str, Any]):
        self._action_plan = value

    @abstractmethod
    def make_decision(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Abstract method for making a decision based on the agent's thoughts.
        Should return a plan of action the agent has decided on.
        """
        pass