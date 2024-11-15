from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class OutputOrchestrator(ABC):
    """
    Abstract base class for the Output Orchestrator, responsible for processing and dispatching
    the output generated by the cognitive system (LLM Brain).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the Output Orchestrator with optional configuration.

        Args:
            config (Optional[Dict[str, Any]]): Configuration settings for the orchestrator.
        """
        self.config = config or {}

    @abstractmethod
    def gate(self, raw_output: Any) -> Any:
        """
        Lightweight distribution method to decide whether to return the output immediately
        or to process it further.

        Args:
            raw_output (Any): The raw output from the LLM Brain.

        Returns:
            Any: Processed or forwarded output.
        """
        pass

    @abstractmethod
    def orchestrate(self, raw_output: Any) -> Dict[str, Any]:
        """
        Heavy processing that translates the brain's output into a structured plan for execution.

        Args:
            raw_output (Any): The raw output from the LLM Brain.

        Returns:
            Dict[str, Any]: The generated plan ready for execution by the action system.
        """
        pass