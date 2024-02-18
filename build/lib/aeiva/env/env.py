from abc import ABC, abstractmethod
from typing import Dict, Tuple, Any, Optional

from aeiva.agent.society import Society


class Environment(ABC):
    """
    Abstract base class for an environment in which agents interact. This follows a similar interface as OpenAI Gym environments.
    """

    def __init__(self, name: str, description: Optional[str] = None, *args, **kwargs):
        self._name = name
        self._description = description
        self._societies = []  # List to store societies present in the environment
        self._resources = {}  # Resources available in the environment

        self._action_space = None  # Specifies the valid actions an agent can take in the environment
        self._observation_space = None  # Specifies the structure of observations an agent can receive from the environment

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> Optional[str]:
        return self._description

    @abstractmethod
    def step(self, action: Any) -> Tuple[Any, float, bool, Dict]:
        """
        Execute one time step within the environment. This should return four values:
        - observation (object): agent's observation of the current environment
        - reward (float) : amount of reward returned after previous action
        - done (bool): whether the episode has ended, in which case further step() calls will return undefined results
        - info (dict): contains auxiliary diagnostic information (helpful for debugging, and sometimes learning)
        """
        pass

    @abstractmethod
    def reset(self) -> Any:
        """
        Resets the state of the environment and returns an initial observation.
        """
        pass

    @abstractmethod
    def render(self, mode: str = 'human'):
        """
        Renders the environment. The set of supported modes varies per environment.
        """
        pass

    @abstractmethod
    def close(self):
        """
        Clean up the environment's resources.
        """
        pass

    @abstractmethod
    def add_society(self, society: Society):
        """
        Abstract method for adding a society to the environment. This should be implemented in a concrete subclass 
        according to the specific behavior of the environment.
        """
        pass

    @abstractmethod
    def remove_society(self, society: Society):
        """
        Abstract method for removing a society from the environment. This should be implemented in a concrete 
        subclass according to the specific behavior of the environment.
        """
        pass

    @property
    @abstractmethod
    def action_space(self) -> 'Space':
        """
        Returns the Space object corresponding to valid actions.
        """
        pass

    @property
    @abstractmethod
    def observation_space(self) -> 'Space':
        """
        Returns the Space object corresponding to valid observations.
        """
        pass
