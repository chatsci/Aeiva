# File: cognition/brain/llm_brain.py

import asyncio
from typing import Any, List, Dict, AsyncGenerator, Optional
import logging
from litellm import supports_response_schema
from aeiva.cognition.brain.base_brain import Brain
from aeiva.llm.llm_client import LLMClient
from aeiva.action.action_envelope import (
    ACTION_SYSTEM_PROMPT,
    ACTION_SYSTEM_PROMPT_AUTO,
    resolve_action_mode,
)
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
        action_cfg = self.config_dict.get("action_config") or {}
        action_mode = resolve_action_mode(action_cfg)
        self.action_mode = action_mode
        self._apply_action_mode(llm_conf_dict, action_mode)

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
            llm_additional_params=llm_conf_dict.get("llm_additional_params") or {},
            llm_custom_provider=llm_conf_dict.get("llm_custom_provider"),
        )
        self.llm_client = LLMClient(self.config)

        system_prompt = self._build_system_prompt(llm_conf_dict, action_cfg, action_mode)
        if system_prompt is not None:  # TODO: only add system prompt for llms that support it.
            self.state["conversation"].append({"role": "system", "content": system_prompt})
        
        logger.info("LLMBrain setup complete.")

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
            
            self.state["conversation"].extend(stimuli)  # keep local history
            messages = self._build_messages_for_llm(stimuli)

            response_parts: List[str] = []
            use_async = use_async or stream  # streaming requires async

            if use_async:
                if stream:
                    async for delta in self.llm_client(
                        messages,
                        tools=None,
                        stream=stream,
                        use_async=True,
                    ):
                        response_parts.append(delta)
                        yield delta
                else:
                    response = await self.llm_client(
                        messages,
                        tools=None,
                        stream=False,
                        use_async=True,
                    )
                    response_parts.append(response)
                    yield response
            else:
                response = await asyncio.to_thread(
                    self.llm_client.generate,
                    messages,
                    None,
                    stream=False,
                )
                response_parts.append(response)
                yield response

            self.state["cognitive_state"] = "".join(response_parts)

        except Exception as e:
            if use_async and not stream:
                try:
                    response = await asyncio.to_thread(
                        self.llm_client.generate,
                        self.state["conversation"],
                        tools=None,
                        stream=False,
                    )
                    self.state["cognitive_state"] = response
                    yield response
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

    def _apply_action_mode(self, llm_conf_dict: Dict[str, Any], action_mode: str) -> None:
        """Apply action mode settings to LLM config without mutating prompts."""
        if action_mode != "json":
            return

        model_name = llm_conf_dict.get("llm_model_name", "gpt-4o")
        llm_api_mode = (llm_conf_dict.get("llm_api_mode") or "auto").lower()
        use_responses_api = llm_api_mode == "responses" or (
            llm_api_mode == "auto" and (model_name.startswith("gpt-5") or "codex" in model_name)
        )
        custom_provider = llm_conf_dict.get("llm_custom_provider")
        additional_params = llm_conf_dict.get("llm_additional_params") or {}
        if use_responses_api:
            additional_params.setdefault("text", {"format": {"type": "json_object"}})
        elif supports_response_schema(model_name, custom_provider):
            additional_params.setdefault("response_format", {"type": "json_object"})
        llm_conf_dict["llm_additional_params"] = additional_params

    def _build_system_prompt(
        self,
        llm_conf_dict: Dict[str, Any],
        action_cfg: Dict[str, Any],
        action_mode: str,
    ) -> Optional[str]:
        system_prompt = llm_conf_dict.get('llm_system_prompt')
        if action_mode == "off":
            return system_prompt

        default_prompt = ACTION_SYSTEM_PROMPT if action_mode == "json" else ACTION_SYSTEM_PROMPT_AUTO
        action_prompt = action_cfg.get("action_system_prompt") or default_prompt
        tool_list = action_cfg.get("tools") or []
        if isinstance(tool_list, list) and tool_list:
            tools_text = self._format_tool_schemas(tool_list)
            action_prompt = f"{action_prompt}\n\nAvailable tools:\n{tools_text}"

        if system_prompt:
            return f"{system_prompt.rstrip()}\n\n{action_prompt}"
        return action_prompt

    def _format_tool_schemas(self, tool_names: List[str]) -> str:
        """
        Format tool schemas for the system prompt.

        Args:
            tool_names: List of tool names to include

        Returns:
            Formatted string with tool name, description, and parameters
        """
        from aeiva.tool.registry import get_registry
        registry = get_registry()

        def type_to_str(t) -> str:
            """Convert Python type to readable string."""
            if hasattr(t, "__name__"):
                return t.__name__
            return str(t).replace("typing.", "")

        lines = []
        for name in tool_names:
            tool = registry.get(name)
            if not tool:
                lines.append(f"- {name}: (not found)")
                continue

            # Format parameters
            params_text = []
            for param in tool.parameters:
                req_marker = "(required)" if param.required else "(optional)"
                default_text = f", default={param.default!r}" if param.default is not None else ""
                type_str = type_to_str(param.type)
                params_text.append(
                    f"    - {param.name}: {type_str} {req_marker}{default_text}"
                    + (f" - {param.description}" if param.description else "")
                )

            params_section = "\n".join(params_text) if params_text else "    (no parameters)"
            lines.append(f"- {name}: {tool.description}\n  Parameters:\n{params_section}")

        return "\n\n".join(lines)
