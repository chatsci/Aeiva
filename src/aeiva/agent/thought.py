from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Thought(ABC):
    """
    Abstract base class for thoughts. This represents the outcome of the agent's cognitive process, based on its observations.
    """
    def __init__(self, *args, **kwargs):
        self.concepts, self.emotions = self.process_thought(*args, **kwargs)

    @property
    def emotions(self) -> Dict[str, float]:
        return self._emotions

    @emotions.setter
    def emotions(self, value: Dict[str, float]):
        self._emotions = value

    @abstractmethod
    def process_thought(self, *args, **kwargs) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Abstract method for processing the agent's thoughts. 
        Should return a dictionary of concepts the agent is considering, and a dictionary of emotional states associated with each concept.
        """
        pass