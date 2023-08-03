from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any


class Society(ABC):
    """
    Abstract base class for a society of agents.
    """

    def __init__(self, society_name: str, society_description: Optional[str] = None, *args, **kwargs):
        self._society_name = society_name
        self._society_description = society_description
        self._members = []  # List to store members of the society
        self._norms = {}  # Dictionary to store societal norms/rules
        self._relationships = {}  # Dictionary to store relationships between members

    @property
    def society_name(self) -> str:
        return self._society_name

    @property
    def society_description(self) -> Optional[str]:
        return self._society_description

    @abstractmethod
    def add_member(self, agent: 'Agent'):
        """
        Abstract method for adding an agent to the society. This should be implemented in a concrete subclass
        according to the specific behavior of the society.
        """
        pass

    @abstractmethod
    def remove_member(self, agent: 'Agent'):
        """
        Abstract method for removing an agent from the society. This should be implemented in a concrete subclass
        according to the specific behavior of the society.
        """
        pass

    @abstractmethod
    def get_relationships(self, agent: 'Agent') -> list[Tuple['Agent', str, float]]:
        """
        Abstract method for getting the relationships of an agent in the society. This should return a list of tuples,
        where each tuple contains an agent, the type of relationship, and the strength of the relationship. This should 
        be implemented in a concrete subclass according to the specific behavior of the society.
        """
        pass

    @abstractmethod
    def set_norms(self, norms: dict[str, Any]):
        """
        Abstract method for setting societal norms/rules. This should be implemented in a concrete subclass according 
        to the specific behavior of the society.
        """
        pass
