from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Observation(ABC):
    """
    Abstract base class for observations. This represents the agent's internal representation of the stimuli.
    The actual processing of raw_data into processed_data is left as an abstract method, allowing subclasses 
    to define the specific transformation pipeline.
    """
    def __init__(self, raw_data: Dict[str, Any], *args, **kwargs):
        self.raw_data = raw_data  # Raw observation data
        self.processed_data = self.process_raw_data(self.raw_data, *args, **kwargs)  # Processed observation data

    @property
    def raw_data(self) -> Dict[str, Any]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, value: Dict[str, Any]):
        self._raw_data = value

    @property
    def processed_data(self) -> Dict[str, Any]:
        return self._processed_data

    @processed_data.setter
    def processed_data(self, value: Dict[str, Any]):
        self._processed_data = value

    @abstractmethod
    def process_raw_data(self, raw_data: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        """
        Abstract method for processing the raw_data. The actual processing pipeline should be defined in subclasses.
        The output is stored in the processed_data attribute.
        """
        pass
