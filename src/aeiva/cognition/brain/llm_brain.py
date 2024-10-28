# File: cognition/brain/llm_brain.py

from typing import Any, List, Dict
from aeiva.cognition.brain.brain import Brain
from aeiva.cognition.brain.llm.llm_client import LLMClient
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
import sys

class LLMBrain(Brain):
    """
    Concrete implementation of the Brain, using an LLM to process stimuli
    and generate cognitive states.

    This brain uses the LLMClient to communicate with a language model to
    process input stimuli and produce outputs.
    """

    def __init__(self, config: LLMGatewayConfig):
        """
        Initialize the LLMBrain with the provided LLM configuration.

        Args:
            config (LLMGatewayConfig): Configuration settings for the LLMBrain.
        """
        super().__init__(config)
        self.llm_client = LLMClient(config)

    def init_state(self) -> Any:
        """
        Initialize the internal state of the Brain.

        The state can track the ongoing conversation or task context.

        Returns:
            dict: Initial empty state.
        """
        return {"conversation": [], "cognitive_state": None}

    def setup(self) -> None:
        """
        Set up the Brain's components.

        For the LLMBrain, this might involve validating the LLM configuration
        and ensuring that all necessary resources are in place.
        """
        # No heavy setup required in this case
        print("LLMBrain setup complete.")

    async def think(self, stimuli: Any, stream: bool = False, tools: List[Dict[str, Any]] = None) -> Any:
        """
        Asynchronously process input stimuli to update the cognitive state.

        Args:
            stimuli (Any): The input stimuli to process.
            stream (bool): Whether to use streaming mode. Default is False.

        Returns:
            str: The full response in both streaming and non-streaming modes.
        """
        try:
            # Assume stimuli is a list of messages (conversation context)
            if not isinstance(stimuli, list):
                raise ValueError("Stimuli must be a list of messages.")

            if stream:
                # Stream mode: collect all parts of the streamed response
                self.state["conversation"] += stimuli  #!! NOTE: to let LLM remember the history. 
                response = ""
                # messages = self.state["conversation"].copy()
                async for delta in self.llm_client.stream_generate(self.state["conversation"], tools=tools):  #!! NOTE: llm client will update conversation
                    response += delta  # Collect the streamed content
                    print(delta, end='', flush=True)
                # self.state["conversation"] += [{"role": "assistant", "content": response}]
                self.state["cognitive_state"] = response
                return response
            else:
                # Non-streaming mode
                self.state["conversation"] += stimuli  #!! NOTE: to let LLM remember the history. 
                # messages = self.state["conversation"].copy()
                response = await self.llm_client.agenerate(self.state["conversation"], tools=tools) #!! NOTE: llm client will update conversation
                # self.state["conversation"] += [{"role": "assistant", "content": response}]
                print("\n\nhistory: ============ ", self.state["conversation"])
                self.state["cognitive_state"] = response
                return response

        except Exception as e:
            self.handle_error(e)
            raise

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during cognitive processing.

        Args:
            error (Exception): The exception that was raised.
        """
        super().handle_error(error)
        # Custom error handling logic for LLM-related issues
        print(f"LLMBrain encountered an error: {error}")