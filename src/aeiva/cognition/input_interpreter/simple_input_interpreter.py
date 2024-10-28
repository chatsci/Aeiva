# File: cognition/input_interpreter/simple_input_interpreter.py

from aeiva.cognition.input_interpreter.input_interpreter import InputInterpreter
from aeiva.perception.stimuli import Stimuli
from aeiva.cognition.observation import Observation
from typing import Optional, Any

class SimpleInputInterpreter(InputInterpreter):
    """
    Simple implementation that optionally processes stimuli into observations.
    """
    def __init__(self, config: Optional[Any] = None):
        self.config = config

    def setup(self) -> None:
        print("SimpleInputInterpreter setup complete.")

    def gate(self, stimuli: Stimuli) -> bool:
        """
        Decide whether to process stimuli or pass through.
        """
        # For simplicity, always process stimuli
        return True

    async def interpret(self, stimuli: Stimuli) -> Observation:
        """
        Convert stimuli into an observation.
        """
        # Simple implementation: extract text data from stimuli
        data = ' '.join([signal.data for signal in stimuli.signals]) # TODO: Check modularity in the future.
        return Observation(data=data)