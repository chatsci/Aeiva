from typing import Any, Dict, Optional
from aeiva.cognition.output_orchestrator.output_orchestrator import OutputOrchestrator


class LLMOutputOrchestrator(OutputOrchestrator):
    """
    A simple implementation of the Output Orchestrator.
    The gate method checks if output needs further orchestration, and the orchestrate method
    returns the original output as a placeholder for now.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.need_orchestrate = False

    def gate(self, raw_output: Any) -> bool:
        """
        Determines if output needs further processing. If the output is a dictionary with a single key-value pair,
        no further orchestration is needed. Otherwise, orchestration is required.

        Args:
            raw_output (Any): The raw output from the cognitive system.

        Returns:
            bool: True if further orchestration is needed, False otherwise.
        """
        if isinstance(raw_output, dict) and len(raw_output) == 1:
            self.need_orchestrate = False
            return False
        else:
            self.need_orchestrate = True
            return True

    def orchestrate(self, raw_output: Any) -> Dict[str, Any]:
        """
        Placeholder method. For now, it just returns the original output.

        Args:
            raw_output (Any): The raw output from the cognitive system.

        Returns:
            Dict[str, Any]: The output wrapped in a dictionary.
        """
        if not self.need_orchestrate:
            return raw_output

        # Placeholder orchestration logic
        self.need_orchestrate = False
        return raw_output
