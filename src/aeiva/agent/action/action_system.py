from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class ActionSystem(ABC):
    """
    Abstract base class for action systems.
    """
    def __init__(self, motor_capacity: Dict[str, Union[int, float]], *args, **kwargs):
        self.motor_capacity = motor_capacity  # The capacity of each motor function of the agent

    @abstractmethod
    def act(self, decision: 'Decision', *args, **kwargs) -> 'Action':
        """
        Abstract method for generating an action based on the given decision.
        """
        pass

    @abstractmethod
    def feedback(self, *args, **kwargs) -> None:
        """
        Abstract method for feedback mechanisms that influence the PerceptionSystem or CognitiveSystem.
        """
        pass