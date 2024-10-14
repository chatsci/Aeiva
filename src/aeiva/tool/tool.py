from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class Tool(ABC):
    """
    Abstract base class for a tool that an agent can use.
    """
    def __init__(self, tool_name: str, tool_description: Optional[str] = None, *args, **kwargs):
        self._tool_name = tool_name
        self._tool_description = tool_description

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def tool_description(self) -> Optional[str]:
        return self._tool_description

    @abstractmethod
    def use_tool(self, *args, **kwargs):
        """
        Abstract method for using the tool. This should be implemented in a concrete subclass
        according to the specific behavior of the tool when used.
        """
        pass
