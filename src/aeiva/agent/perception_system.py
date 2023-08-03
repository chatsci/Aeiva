from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class PerceptionSystem(ABC):
    """
    Abstract base class for perception systems.
    """
    def __init__(self, sensory_capacity: Dict[str, Union[int, float]], *args, **kwargs):
        self.sensory_capacity = sensory_capacity  # The capacity of each sensory organ of the agent

    @abstractmethod
    def perceive(self, stimuli: 'Stimuli', *args, **kwargs) -> 'Observation':
        """
        Abstract method for processing the given stimuli into an internal observation.
        """
        pass

    @abstractmethod
    def hierarchical_processing(self, *args, **kwargs) -> 'Observation':
        """
        Abstract method for hierarchical processing of stimuli.
        """
        pass