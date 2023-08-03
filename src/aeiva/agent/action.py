from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Action(ABC):
    """
    Abstract base class for actions. This represents a behavior or operation carried out by the agent, based on its decision.
    """
    def __init__(self, *args, **kwargs):
        self.actions = self.perform_action(*args, **kwargs)

    @property
    def actions(self) -> List[str]:
        return self._actions

    @actions.setter
    def actions(self, value: List[str]):
        self._actions = value

    @abstractmethod
    def perform_action(self, *args, **kwargs) -> List[str]:
        """
        Abstract method for performing an action based on the agent's decision.
        Should return a list of actions to be performed by the agent.
        """
        pass
