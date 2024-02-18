from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Union, Optional, Tuple
from collections import deque


class Role(ABC):
    """
    Abstract base class for the role of an agent in a society.
    """
    def __init__(self, role_name: str, role_description: Optional[str] = None, *args, **kwargs):
        self._role_name = role_name
        self._role_description = role_description

    @property
    def role_name(self) -> str:
        return self._role_name

    @property
    def role_description(self) -> Optional[str]:
        return self._role_description

    @abstractmethod
    def define_role(self, *args, **kwargs):
        pass