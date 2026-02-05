"""
Chat/Completions API Handler.

Handles the standard OpenAI chat/completions API format.
"""

from typing import Any, Dict, List, Optional, Tuple

from litellm import (
    acompletion as llm_acompletion,
    completion as llm_completion,
    get_supported_openai_params,
    supports_function_calling,
)

from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.api_handlers.base import BaseHandler
from aeiva.llm.tool_types import ToolCall, ToolCallDelta


class ChatAPIHandler(BaseHandler):
    """
    Handler for OpenAI Chat/Completions API.

    Used by: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-5, o1-*, o3-*, etc.
    """

    def __init__(self, config: LLMGatewayConfig):
        super().__init__(config)

    def _resolve_tool_choice(
        self,
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Any,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Any], Optional[str]]:
        if tool_choice is None:
            return tools, None, None

        if isinstance(tool_choice, str):
            lowered = tool_choice.lower()
            if lowered in {"auto", "none", "required"}:
                tool_choice = lowered
            else:
                tool_choice = {"type": "function", "function": {"name": tool_choice}}

        if tool_choice == "none":
            return [], "none", None

        if tool_choice == "required":
            if not tools:
                raise ValueError("tool_choice=required but no tools were provided")
            return tools, "required", "You must call one of the available tools before responding."

        if isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
            target = (tool_choice.get("function") or {}).get("name")
            if not target:
                raise ValueError("tool_choice.function.name is required")
            matched = [t for t in (tools or []) if (t.get("function") or {}).get("name") == target]
            if not matched:
                raise ValueError(f"tool_choice requested unknown tool: {target}")
            return matched, tool_choice, f"You must call the {target} tool before responding."

        return tools, tool_choice, None

    def _inject_system_prompt(
        self,
        messages: List[Dict[str, Any]],
        extra_prompt: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not extra_prompt:
            return messages

        new_messages = [dict(m) for m in messages]
        if new_messages and new_messages[0].get("role") == "system":
            content = new_messages[0].get("content") or ""
            if isinstance(content, str):
                new_messages[0]["content"] = f"{content}\n\n{extra_prompt}".strip()
            else:
                new_messages[0]["content"] = content
                new_messages.insert(0, {"role": "system", "content": extra_prompt})
        else:
            new_messages.insert(0, {"role": "system", "content": extra_prompt})
        return new_messages

    def build_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build chat/completions API parameters."""
        model_name = (self.config.llm_model_name or "").lower()

        tool_choice = kwargs.pop("tool_choice", None)
        if tool_choice is None:
            tool_choice = getattr(self.config, "llm_tool_choice", None)

        resolved_tools, resolved_choice, extra_prompt = self._resolve_tool_choice(tools, tool_choice)
        resolved_messages = self._inject_system_prompt(messages, extra_prompt)

        params = {
            "model": self.config.llm_model_name,
            "messages": resolved_messages,
            "temperature": self.config.llm_temperature,
            "top_p": self.config.llm_top_p,
            "max_tokens": self.config.llm_max_output_tokens,
            "timeout": self.config.llm_timeout,
        }

        # Some models don't support temperature/top_p
        if self._should_drop_sampling_params(model_name):
            params.pop("temperature", None)
            params.pop("top_p", None)

        self._add_auth_params(params)
        self._add_additional_params(params, **kwargs)
        params = self._filter_supported_params(params)

        # Add tools if model supports function calling
        if resolved_tools and supports_function_calling(self.config.llm_model_name):
            params["tools"] = resolved_tools
            if resolved_choice is not None:
                params["tool_choice"] = resolved_choice

        return params

    def _should_drop_sampling_params(self, model_name: str) -> bool:
        """Check if model doesn't support temperature/top_p."""
        # gpt-5 and codex models with reasoning don't support these
        if model_name.startswith("gpt-5") or "codex" in model_name:
            reasoning_effort = None
            if isinstance(self.config.llm_additional_params, dict):
                reasoning_effort = self.config.llm_additional_params.get("reasoning_effort")
            if reasoning_effort != "none":
                return True
        return False

    def _filter_supported_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter to only parameters supported by the model."""
        model_name = params.get("model")
        custom_provider = params.get("custom_llm_provider")
        supported = get_supported_openai_params(model_name, custom_provider)

        if not supported:
            return params

        supported_set = set(supported)

        # Handle max_tokens aliases
        if "max_output_tokens" in supported_set and "max_tokens" in params:
            params["max_output_tokens"] = params.pop("max_tokens")
        elif "max_completion_tokens" in supported_set and "max_tokens" in params:
            params["max_completion_tokens"] = params.pop("max_tokens")

        # Always keep these base keys
        base_keys = {
            "model", "messages", "api_key", "base_url",
            "api_version", "timeout", "custom_llm_provider",
        }

        for key in list(params.keys()):
            if key not in base_keys and key not in supported_set:
                params.pop(key)

        return params

    def parse_response(
        self,
        response: Any,
    ) -> Tuple[Optional[Any], List[ToolCall], str]:
        """Parse chat/completions API response."""
        message = None
        tool_calls: List[ToolCall] = []
        content = ""

        # Handle object response
        if hasattr(response, "choices"):
            choices = getattr(response, "choices") or []
            if choices:
                message = getattr(choices[0], "message", None)
                if message is None and hasattr(choices[0], "delta"):
                    message = choices[0].delta
            if message is not None:
                content = getattr(message, "content", None) or ""
                tool_calls = self._normalize_tool_calls(getattr(message, "tool_calls", None))
                return message, tool_calls, content

        # Handle dict response
        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                msg = choices[0].get("message") or choices[0].get("delta") or {}
                content = msg.get("content") or ""
                tool_calls = self._normalize_tool_calls(msg.get("tool_calls"))
                return msg, tool_calls, content

        # Handle string response
        if isinstance(response, str):
            return None, [], response

        return None, [], ""

    def parse_stream_delta(
        self,
        chunk: Any,
        **kwargs,
    ) -> Tuple[Optional[str], Optional[List[ToolCallDelta]]]:
        """Parse streaming chunk from chat/completions API."""
        # Handle object with choices
        if hasattr(chunk, "choices"):
            choices = getattr(chunk, "choices") or []
            if choices and hasattr(choices[0], "delta"):
                delta = choices[0].delta
                delta_content = getattr(delta, "content", None)
                delta_tool_calls = getattr(delta, "tool_calls", None)
                if not delta_tool_calls and hasattr(choices[0], "message"):
                    message = getattr(choices[0], "message", None)
                    delta_tool_calls = getattr(message, "tool_calls", None) if message else None
                return delta_content, self._normalize_tool_call_deltas(delta_tool_calls)

        # Handle dict response
        if isinstance(chunk, dict):
            choices = chunk.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                tool_calls = delta.get("tool_calls")
                if not tool_calls:
                    message = choices[0].get("message") or {}
                    tool_calls = message.get("tool_calls")
                return delta.get("content"), self._normalize_tool_call_deltas(tool_calls)

        # Handle string
        if isinstance(chunk, str):
            return chunk, None

        return None, None

    def _normalize_tool_calls(self, tool_calls: Any) -> List[ToolCall]:
        if not tool_calls:
            return []
        calls: List[ToolCall] = []
        for item in tool_calls:
            call = ToolCall.from_any(item)
            if call:
                calls.append(call)
        return calls

    def _normalize_tool_call_deltas(self, tool_calls: Any) -> Optional[List[ToolCallDelta]]:
        if not tool_calls:
            return None
        deltas: List[ToolCallDelta] = []
        for item in tool_calls:
            delta = ToolCallDelta.from_any(item)
            if delta:
                deltas.append(delta)
        return deltas or None

    async def execute(
        self,
        params: Dict[str, Any],
        stream: bool = False,
    ) -> Any:
        """Execute chat/completions API call."""
        params["stream"] = stream
        return await self._execute_with_fallback(llm_acompletion, params)

    def execute_sync(
        self,
        params: Dict[str, Any],
    ) -> Any:
        """Execute chat/completions API call synchronously."""
        params["stream"] = False
        return self._execute_with_fallback_sync(llm_completion, params)
