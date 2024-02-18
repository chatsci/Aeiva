from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class CognitiveSystem(ABC):
    """
    Abstract base class for cognitive systems.
    """
    def __init__(self, memory: 'Memory', world_model: 'WorldModel', *args, **kwargs):
        self.memory = memory  # The memory system of the agent
        self.world_model = world_model  # The world model of the agent

    @abstractmethod
    def think(self, observation: 'Observation', *args, **kwargs) -> 'Thought':
        """
        Abstract method for generating a thought based on the given observation.
        """
        pass

    @abstractmethod
    def parallel_processing(self, *args, **kwargs) -> 'Thought':
        """
        Abstract method for parallel processing of different types of cognitive processes.
        """
        pass

