# File: cognition/brain/llm_brain.py

from typing import Any, List, Dict, AsyncGenerator, Optional
from aeiva.cognition.brain.brain import Brain
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
import sys

class LLMBrain(Brain):
    """
    Concrete implementation of the Brain, using an LLM to process stimuli
    and generate cognitive states.

    This brain uses the LLMClient to communicate with a language model to
    process input stimuli and produce outputs.
    """

    def __init__(self, config: Dict):
        """
        Initialize the LLMBrain with the provided LLM configuration.

        Args:
            config (LLMGatewayConfig): Configuration settings for the LLMBrain.
        """
        super().__init__(config)
        self.config_dict = config
        self.config = None
        self.llm_client = None

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
        llm_conf_dict = self.config_dict.get('llm_gateway_config', {})
        self.config = LLMGatewayConfig(
            llm_api_key=llm_conf_dict.get('llm_api_key'),
            llm_model_name=llm_conf_dict.get('llm_model_name', 'gpt-4o'),
            llm_temperature=llm_conf_dict.get('llm_temperature', 0.7),
            llm_max_output_tokens=llm_conf_dict.get('llm_max_output_tokens', 10000),
            llm_use_async=llm_conf_dict.get('llm_use_async', False),
            llm_stream=llm_conf_dict.get('llm_stream', False)
        )
        self.llm_client = LLMClient(self.config)

        system_prompt = llm_conf_dict.get('llm_system_prompt', None)
        if system_prompt is not None:  # TODO: only add system prompt for llms that support it.
                self.state["conversation"] += [{ "role": "system", "content": system_prompt }]
        
        print("LLMBrain setup complete.")

    async def think(
            self,
            stimuli: Any,
            tools: List[Dict[str, Any]] = None,
            stream: bool = False,
            use_async: bool = False
            ) -> AsyncGenerator[str, None]:
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
            
            self.state["conversation"] += stimuli  #!! NOTE: to let LLM remember the history. 

            if not use_async: # NOTE: stream mode only works when use_async!!!
                response = self.llm_client(self.state["conversation"], tools=tools, stream=stream) #!! NOTE: llm client will update conversation
                # self.state["conversation"] += [{"role": "assistant", "content": response}]
                self.state["cognitive_state"] = response
                yield response
            elif stream:
                # Stream mode: collect all parts of the streamed response
                response = ""
                # messages = self.state["conversation"].copy()
                async for delta in self.llm_client(self.state["conversation"], tools=tools, stream=stream):  #!! NOTE: llm client will update conversation
                    response += delta  # Collect the streamed content
                    yield delta
                # self.state["conversation"] += [{"role": "assistant", "content": response}]
                self.state["cognitive_state"] = response
                #return response
            else:
                # messages = self.state["conversation"].copy()
                response = await self.llm_client(self.state["conversation"], tools=tools, stream=stream) #!! NOTE: llm client will update conversation
                # self.state["conversation"] += [{"role": "assistant", "content": response}]
                self.state["cognitive_state"] = response
                yield response
                #return response

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