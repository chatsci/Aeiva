from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Background(ABC):
    """
    Abstract base class for the background of an agent in a society.
    """
    def __init__(self, background_info: Dict[str, Any], *args, **kwargs):
        self._background_info = background_info

    @property
    def background_info(self) -> Dict[str, Any]:
        return self._background_info

    def add_background_info(self, key: str, value: Any):
        self._background_info[key] = value

    @abstractmethod
    def update_background(self, *args, **kwargs):
        pass