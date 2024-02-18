from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Profile(ABC):
    """
    Abstract base class for the background of an agent in a society.
    """
    def __init__(self, profile: Dict[str, Any], *args, **kwargs):
        self._profile = profile

    @property
    def profile(self) -> Dict[str, Any]:
        return self._profile

    def add_profile(self, key: str, value: Any):
        self._profile[key] = value

    @abstractmethod
    def update_profile(self, *args, **kwargs):
        pass