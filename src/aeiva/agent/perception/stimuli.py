from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Stimuli(ABC):
    """
    Abstract base class for stimuli. This could be any information that an agent can perceive from the environment.
    The actual process of generating sensory_data is left as an abstract method, allowing subclasses to define 
    the specific data generation.
    """
    def __init__(self, *args, **kwargs):
        self.sensory_data = self.generate_sensory_data(*args, **kwargs)  # A dictionary containing various types of sensory data

    @property
    def sensory_data(self) -> Dict[str, Any]:
        return self._sensory_data

    @sensory_data.setter
    def sensory_data(self, value: Dict[str, Any]):
        self._sensory_data = value

    @abstractmethod
    def generate_sensory_data(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Abstract method for generating the sensory_data. The actual generation should be defined in subclasses.
        The output is stored in the sensory_data attribute.
        """
        pass
