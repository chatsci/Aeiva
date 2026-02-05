# File: cognition/brain/llm_brain.py

import asyncio
from typing import Any, List, Dict, AsyncGenerator, Optional
import logging
from aeiva.cognition.brain.base_brain import Brain
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig

logger = logging.getLogger(__name__)

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
        llm_api_key = llm_conf_dict.get('llm_api_key')
        self.config = LLMGatewayConfig(
            llm_api_key=llm_api_key,
            llm_model_name=llm_conf_dict.get('llm_model_name', 'gpt-4o'),
            llm_temperature=llm_conf_dict.get('llm_temperature', 0.7),
            llm_max_output_tokens=llm_conf_dict.get('llm_max_output_tokens', 10000),
            llm_timeout=llm_conf_dict.get('llm_timeout', 120),
            llm_use_async=llm_conf_dict.get('llm_use_async', False),
            llm_stream=llm_conf_dict.get('llm_stream', False),
            llm_api_mode=llm_conf_dict.get("llm_api_mode", "auto"),
            llm_tool_choice=llm_conf_dict.get("llm_tool_choice"),
            llm_additional_params=llm_conf_dict.get("llm_additional_params") or {},
            llm_custom_provider=llm_conf_dict.get("llm_custom_provider"),
        )
        self.llm_client = LLMClient(self.config)

        system_prompt = self._build_system_prompt(llm_conf_dict)
        if system_prompt is not None:  # TODO: only add system prompt for llms that support it.
            self.state["conversation"].append({"role": "system", "content": system_prompt})
        
        logger.info("LLMBrain setup complete.")

    async def think(
            self,
            stimuli: Any,
            tools: List[Dict[str, Any]] = None,
            stream: bool = False,
            use_async: bool = False,
            tool_choice: Any = None,
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
            
            self.state["conversation"].extend(stimuli)  # keep local history
            messages = self._build_messages_for_llm(stimuli)

            response_parts: List[str] = []
            use_async = use_async or stream  # streaming requires async

            if use_async:
                if stream:
                    extra = {"tool_choice": tool_choice} if tool_choice is not None else {}
                    async for delta in self.llm_client.astream(
                        messages,
                        tools=tools,
                        stream=stream,
                        **extra,
                    ):
                        response_parts.append(delta)
                        yield delta
                else:
                    extra = {"tool_choice": tool_choice} if tool_choice is not None else {}
                    result = await self.llm_client.arun(
                        messages,
                        tools=tools,
                        stream=False,
                        **extra,
                    )
                    response_parts.append(result.text)
                    yield result.text
            else:
                extra = {"tool_choice": tool_choice} if tool_choice is not None else {}
                result = await asyncio.to_thread(
                    self.llm_client.run,
                    messages,
                    tools,
                    stream=False,
                    **extra,
                )
                response_parts.append(result.text)
                yield result.text

            self.state["cognitive_state"] = "".join(response_parts)

        except Exception as e:
            if use_async and not stream:
                try:
                    result = await asyncio.to_thread(
                        self.llm_client.run,
                        self.state["conversation"],
                        tools=tools,
                        stream=False,
                    )
                    self.state["cognitive_state"] = result.text
                    yield result.text
                    return
                except Exception:
                    pass
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
        logger.error("LLMBrain encountered an error: %s", error)

    def _build_messages_for_llm(self, stimuli: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build minimal message list for LLM calls."""
        return self.state["conversation"]

    def _build_system_prompt(self, llm_conf_dict: Dict[str, Any]) -> Optional[str]:
        """Return the base system prompt without action JSON instructions."""
        return llm_conf_dict.get('llm_system_prompt')
