from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class InputInterpreter(ABC):
    """
    Abstract base class for the Input Interpreter, responsible for processing incoming stimuli
    and determining how to format and forward them to the cognition system (LLM Brain).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def gate(self, raw_input: Any) -> Any:
        """
        Lightweight gate that determines whether the input can be forwarded directly to the brain
        or if further processing is needed.
        """
        pass

    @abstractmethod
    def interpret(self, raw_input: Any) -> Dict[str, Any]:
        """
        Heavy processing that aggregates and formats the raw input into structured stimuli/prompt
        that the brain can better handle.
        """
        pass