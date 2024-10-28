from typing import Any, Dict, Optional
from aeiva.cognition.input_interpreter.input_interpreter import InputInterpreter


class LLMInputInterpreter(InputInterpreter):
    """
    A simple implementation of the Input Interpreter.
    The gate method checks if input needs further interpretation, and the interpret method
    returns the original input as a placeholder for now.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.need_interpret = False

    def gate(self, raw_input: Any) -> bool:
        """
        Determines if input needs further processing. If the input is a dictionary with a single key-value pair,
        no further interpretation is needed. Otherwise, interpretation is required.
        """
        if isinstance(raw_input, dict) and len(raw_input) == 1:
            self.need_interpret = False
            return False
        else:
            self.need_interpret = True
            return True

    def interpret(self, raw_input: Any) -> Dict[str, Any]:
        """
        Placeholder method. For now, it just returns the original input.
        """
        if not self.need_interpret:
            return raw_input

        # TODO: add LLM to interpret
        
        self.need_interpret = False
        return raw_input
