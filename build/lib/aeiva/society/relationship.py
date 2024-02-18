from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Relationship(ABC):
    """
    Abstract base class for the relationship between agents in a society.
    """
    def __init__(self, agent1: 'Agent', agent2: 'Agent', relationship_type: str, relationship_strength: float, *args, **kwargs):
        self._agent1 = agent1
        self._agent2 = agent2
        self._relationship_type = relationship_type
        self._relationship_strength = relationship_strength

    @property
    def agents(self) -> Tuple['Agent', 'Agent']:
        return self._agent1, self._agent2

    @property
    def relationship_type(self) -> str:
        return self._relationship_type

    @property
    def relationship_strength(self) -> float:
        return self._relationship_strength

    @relationship_strength.setter
    def relationship_strength(self, new_strength: float):
        self._relationship_strength = new_strength

    @abstractmethod
    def update_relationship(self, *args, **kwargs):
        pass