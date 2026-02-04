import json
import re
import requests
from typing import Dict, Any, AsyncGenerator, List, Optional, Tuple, Union

import litellm
from litellm import (
    completion as llm_completion,
    acompletion as llm_acompletion,
    responses as llm_responses,
    aresponses as llm_aresponses,
    supports_function_calling,
    get_supported_openai_params,
)

# Enable litellm to automatically drop unsupported parameters
# This handles model-specific restrictions (e.g., gpt-5 only supports temperature=1)
litellm.drop_params = True


def _patch_responses_api_usage() -> None:
    """
    Patch litellm's ResponsesAPIResponse.model_dump to coerce usage before serialization.

    Root cause: litellm's logging calls model_dump() on ResponsesAPIResponse, but the 'usage'
    field may still be a dict (not ResponseAPIUsage), causing Pydantic serialization warnings.

    Fix: Override model_dump to coerce usage to ResponseAPIUsage before Pydantic serializes it.
    """
    try:
        from litellm.types.llms.openai import ResponsesAPIResponse, ResponseAPIUsage
    except ImportError:
        return

    if getattr(ResponsesAPIResponse, "_model_dump_patched", False):
        return

    def _coerce_usage(usage: Any) -> Any:
        """Convert usage dict to ResponseAPIUsage if needed."""
        if usage is None or not isinstance(usage, dict):
            return usage
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        total_tokens = usage.get("total_tokens") or (input_tokens + output_tokens)
        return ResponseAPIUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    original_model_dump = ResponsesAPIResponse.model_dump

    def patched_model_dump(self, *args, **kwargs):
        # Coerce usage before serialization to avoid Pydantic warning
        if isinstance(self.usage, dict):
            try:
                object.__setattr__(self, "usage", _coerce_usage(self.usage))
            except Exception:
                pass
        return original_model_dump(self, *args, **kwargs)

    ResponsesAPIResponse.model_dump = patched_model_dump
    ResponsesAPIResponse._model_dump_patched = True


# Apply patch at module load time
_patch_responses_api_usage()

from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.llm_gateway_exceptions import (
    LLMGatewayError,
    llm_gateway_exception,
)
from aeiva.llm.fault_tolerance import retry_async, retry_sync
from aeiva.llm.llm_usage_metrics import LLMUsageMetrics
from aeiva.tool.registry import get_registry
import logging

MAX_TOOL_CALL_LOOP = 10 # TODO: This is used in case LLM recursively call tools. Make it a config param. 

class LLMClient:
    """
    Language Model interface that supports synchronous, asynchronous, and streaming modes,
    and optionally, tool usage via function calls.
    """

    def __init__(self, config: LLMGatewayConfig):
        self.config = config
        self.metrics = LLMUsageMetrics()
        self.logger = logging.getLogger(__name__)
        self._responses_param_keys = self._get_responses_param_keys()
        self.last_response_id: Optional[str] = None
        self._unsupported_params: Dict[str, set] = {}
        self._validate_config()
        self._configure_litellm()

    def _validate_config(self):
        if not self.config.llm_api_key:
            raise ValueError("API key must be provided in the configuration.")

    def _configure_litellm(self) -> None:
        """Configure global litellm settings for model compatibility."""
        if hasattr(litellm, "suppress_debug_info"):
            litellm.suppress_debug_info = True
        if self.config.llm_api_key:
            litellm.api_key = self.config.llm_api_key
            litellm.openai_key = self.config.llm_api_key

    def _extract_unsupported_param(self, error: Exception) -> Optional[str]:
        message = str(error)
        patterns = [
            r"Unsupported parameter: ['\"]([^'\"]+)['\"]",
            r"parameter ['\"]([^'\"]+)['\"] is not supported",
            r"['\"]([^'\"]+)['\"] is not supported with this model",
            r"does not support (?:the )?parameter ['\"]([^'\"]+)['\"]",
            r"does not support (?:the )?parameters?:\s*([a-zA-Z0-9_]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _drop_unsupported_param(self, params: Dict[str, Any], error: Exception) -> bool:
        param = self._extract_unsupported_param(error)
        if not param:
            return False
        alias_map = {
            "max_tokens": "max_output_tokens",
            "max_completion_tokens": "max_output_tokens",
            "text.format": "text",
        }
        if param in params:
            params.pop(param, None)
            model_name = params.get("model")
            if model_name:
                self._unsupported_params.setdefault(model_name, set()).add(param)
            return True
        alias = alias_map.get(param)
        if alias and alias in params:
            params.pop(alias, None)
            model_name = params.get("model")
            if model_name:
                self._unsupported_params.setdefault(model_name, set()).add(alias)
            return True
        return False

    def _strip_cached_unsupported_params(self, params: Dict[str, Any]) -> None:
        model_name = params.get("model")
        if not model_name:
            return
        blocked = self._unsupported_params.get(model_name)
        if not blocked:
            return
        for key in list(blocked):
            params.pop(key, None)

    def _call_with_param_fallback(self, call_fn, params: Dict[str, Any]):
        self._strip_cached_unsupported_params(params)
        for attempt in range(3):
            try:
                return call_fn(**params)
            except Exception as error:
                if self._drop_unsupported_param(params, error):
                    continue
                raise

    async def _acall_with_param_fallback(self, call_fn, params: Dict[str, Any]):
        self._strip_cached_unsupported_params(params)
        for attempt in range(3):
            try:
                return await call_fn(**params)
            except Exception as error:
                if self._drop_unsupported_param(params, error):
                    continue
                raise

    @retry_sync(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),  # Catching LLMGatewayError
    )
    def generate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> str:
        try:
            if self._use_responses_api(messages, tools):
                params = self._build_responses_params(messages=messages, tools=tools, **kwargs)
                response = self._call_with_param_fallback(llm_responses, params)
                self._update_metrics(response)
                _, _, content = self._extract_message(response)
                self._update_last_response_id(response)
                messages.append({"role": "assistant", "content": content})
                return content

            max_iterations = MAX_TOOL_CALL_LOOP  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Build parameters
                params = self._build_params(messages=messages, tools=tools, **kwargs)
                response = self._call_with_param_fallback(llm_completion, params)
                self._update_metrics(response)
                response_message, tool_calls, content = self._extract_message(response)

                if tool_calls:
                    self._execute_tool_calls_sync(messages, tool_calls)
                    continue
                else:
                    # Assistant provided a final response
                    messages.append({"role": "assistant", "content": content})
                    return content

            # If loop exceeds max iterations
            raise Exception("Maximum iterations reached without a final response.")

        except Exception as e:
            self.logger.error(f"LLM Gateway Error: {e}")
            raise llm_gateway_exception(e)

    @retry_async(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),  # Catching LLMGatewayError
    )
    async def agenerate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> str:
        try:
            if self._use_responses_api(messages, tools):
                params = self._build_responses_params(messages=messages, tools=tools, **kwargs)
                response = await self._acall_with_param_fallback(llm_aresponses, params)
                self._update_metrics(response)
                _, _, content = self._extract_message(response)
                self._update_last_response_id(response)
                messages.append({"role": "assistant", "content": content})
                return content

            max_iterations = MAX_TOOL_CALL_LOOP  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Build parameters
                params = self._build_params(messages=messages, tools=tools, **kwargs)
                response = await self._acall_with_param_fallback(llm_acompletion, params)
                self._update_metrics(response)
                response_message, tool_calls, content = self._extract_message(response)

                if tool_calls:
                    await self._execute_tool_calls_async(messages, tool_calls)
                    continue
                else:
                    # Assistant provided a final response
                    messages.append({"role": "assistant", "content": content})
                    return content

            # If loop exceeds max iterations
            raise Exception("Maximum iterations reached without a final response.")

        except Exception as e:
            self.logger.error(f"LLM Asynchronous Generation Error: {e}")
            raise llm_gateway_exception(e)

    async def stream_generate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
            max_iterations = MAX_TOOL_CALL_LOOP  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                if self._use_responses_api(messages, tools):
                    params = self._build_responses_params(messages=messages, tools=tools, **kwargs)
                    if params.get("stream") is not True:
                        response = await self.agenerate(messages, tools=tools, stream=False)
                        if response:
                            yield response
                        return
                    response_stream = await self._acall_with_param_fallback(llm_aresponses, params)
                else:
                    # Build parameters
                    params = self._build_params(messages=messages, tools=tools, **kwargs)
                    if params.get("stream") is not True:
                        response = await self.agenerate(messages, tools=tools, stream=False)
                        if response:
                            yield response
                        return
                    response_stream = await self._acall_with_param_fallback(llm_acompletion, params)

                # Prepare to collect the assistant's reply
                tool_calls = []  # Accumulator for tool calls
                full_delta_content = ''  # Accumulator for assistant's content
                completed_response_obj = None

                # Collect streamed responses
                async for response in response_stream:
                    response_type = getattr(response, "type", None)
                    if response_type and str(response_type).endswith("response.completed"):
                        completed_response_obj = getattr(response, "response", None)
                    delta_content, delta_tool_calls = self._extract_stream_delta(
                        response,
                        response_type=response_type,
                        has_accumulated=bool(full_delta_content),
                    )

                    if delta_content:
                        if full_delta_content and isinstance(delta_content, str):
                            if delta_content.startswith(full_delta_content):
                                incremental = delta_content[len(full_delta_content):]
                                if incremental:
                                    yield incremental
                                full_delta_content = delta_content
                            else:
                                full_delta_content += delta_content
                                yield delta_content
                        else:
                            full_delta_content += delta_content
                            yield delta_content

                    if delta_tool_calls:
                        for tc_chunk in delta_tool_calls:
                            index = getattr(tc_chunk, "index", None)
                            if index is None:
                                index = len(tool_calls)
                            while len(tool_calls) <= index:
                                tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                            tc = tool_calls[index]

                            if getattr(tc_chunk, 'id', None):
                                tc["id"] += tc_chunk.id
                            if getattr(tc_chunk, 'function', None) is not None:
                                if getattr(tc_chunk.function, 'name', None):
                                    tc["function"]["name"] += tc_chunk.function.name
                                if getattr(tc_chunk.function, 'arguments', None):
                                    tc["function"]["arguments"] += tc_chunk.function.arguments

                # After initial streaming, check if there are tool calls
                if tool_calls and not self._use_responses_api(messages, tools):
                    await self._execute_tool_calls_async(messages, tool_calls, available_tools=tools)
                    continue
                else:
                    # No tool calls, streaming is complete
                    if not full_delta_content and completed_response_obj is not None:
                        _, _, completed_text = self._extract_message(completed_response_obj)
                        full_delta_content = completed_text or full_delta_content
                        if full_delta_content:
                            yield full_delta_content
                    if completed_response_obj is not None:
                        self._update_metrics(completed_response_obj)
                        self._update_last_response_id(completed_response_obj)
                    messages.append({"role": "assistant", "content": full_delta_content})
                    return  # Exit the loop

            # If loop exceeds max iterations
            yield "Maximum iterations reached without a final response."

        except Exception as e:
            self.logger.error(f"Streaming LLM Gateway Error: {e}")
            try:
                response = await self.agenerate(messages, tools=tools, stream=False)
                if response:
                    yield response
                    return
            except Exception as fallback_error:
                self.logger.error(f"Streaming fallback failed: {fallback_error}")
            yield f"An error occurred during streaming: {e}"

    def call_tool_via_server(self, api_name: str, function_name: str, params: Dict[str, Any]) -> Any: # TODO: may need revise
        """Calls the API via FastAPI server."""
        url = f"http://localhost:8000/api/{api_name}/{function_name}"
        self.logger.info(f"Calling {api_name} with params: {params}")
        response = requests.get(url, params=params)
        if response.status_code == 200:
            json_response = response.json()
            if "result" in json_response:
                return str(json_response["result"])
            else:
                return f"Error from API: {json_response.get('error', 'Unknown error')}"
        else:
            return f"HTTP Error {response.status_code}: {response.text}"

    async def call_tool(self, api_name: str, function_name: str, params: Dict[str, Any]) -> Any:
        """Calls a tool via the registry."""
        registry = get_registry()
        return await registry.execute(api_name, **params)

    def call_tool_sync(self, api_name: str, function_name: str, params: Dict[str, Any]) -> Any:
        """Calls a tool synchronously via the registry."""
        registry = get_registry()
        return registry.execute_sync(api_name, **params)

    def _execute_tool_calls_sync(self, messages: List[Any], tool_calls: List[Any]) -> None:
        messages.append({"role": "assistant", "tool_calls": tool_calls})
        for tool_call in tool_calls:
            function_name, function_args, tool_call_id = self._parse_tool_call(tool_call)
            try:
                function_response = self.call_tool_sync(
                    api_name=function_name, function_name=function_name, params=function_args
                )
            except Exception as e:
                self.logger.error(f"Error executing tool '{function_name}': {e}")
                function_response = f"Error executing tool '{function_name}': {e}"
            messages.append(
                {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                }
            )

    async def _execute_tool_calls_async(
        self,
        messages: List[Any],
        tool_calls: List[Any],
        *,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        messages.append({"role": "assistant", "tool_calls": tool_calls})
        available_names = None
        if available_tools:
            available_names = {tool["function"]["name"] for tool in available_tools if "function" in tool}
        for tool_call in tool_calls:
            function_name, function_args, tool_call_id = self._parse_tool_call(tool_call)
            if available_names is not None and function_name not in available_names:
                self.logger.error(f"Function {function_name} does not exist.")
                messages.append(
                    {
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Function {function_name} does not exist.",
                    }
                )
                continue
            try:
                function_response = await self.call_tool(
                    api_name=function_name, function_name=function_name, params=function_args
                )
            except Exception as e:
                self.logger.error(f"Error executing tool '{function_name}': {e}")
                function_response = f"Error executing tool '{function_name}': {e}"
            messages.append(
                {
                    "tool_call_id": tool_call_id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                }
            )

    def _parse_tool_call(self, tool_call: Any) -> Tuple[str, Dict[str, Any], str]:
        if isinstance(tool_call, dict):
            function = tool_call.get("function") or {}
            function_name = function.get("name") or ""
            arguments = function.get("arguments") or "{}"
            tool_call_id = tool_call.get("id") or ""
        else:
            function_name = tool_call.function.name
            arguments = tool_call.function.arguments
            tool_call_id = tool_call.id
        try:
            function_args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding function arguments: {e}")
            function_args = {}
        return function_name, function_args, tool_call_id

    def _build_params(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        model_name = (self.config.llm_model_name or "").lower()
        params = {
            "model": self.config.llm_model_name,
            "messages": messages,
            "temperature": self.config.llm_temperature,
            "top_p": self.config.llm_top_p,
            "max_tokens": self.config.llm_max_output_tokens,
            "timeout": self.config.llm_timeout,
        }
        if model_name.startswith("gpt-5") or "codex" in model_name:
            reasoning_effort = None
            if isinstance(self.config.llm_additional_params, dict):
                reasoning_effort = self.config.llm_additional_params.get("reasoning_effort")
            if reasoning_effort != "none":
                params.pop("temperature", None)
                params.pop("top_p", None)
        if self.config.llm_api_key:
            params["api_key"] = self.config.llm_api_key
        if self.config.llm_base_url:
            params["base_url"] = self.config.llm_base_url
        if self.config.llm_api_version:
            params["api_version"] = self.config.llm_api_version
        if self.config.llm_custom_provider:
            params["custom_llm_provider"] = self.config.llm_custom_provider
        params.update(self.config.llm_additional_params)
        params.update(kwargs)

        params = self._filter_supported_params(params)

        # Check if the model supports function calling
        if tools and supports_function_calling(self.config.llm_model_name):
            params["tools"] = tools
            params["tool_choice"] = "auto"

        return params

    def _build_responses_params(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        input_payload, instructions = self._normalize_responses_input(messages)
        model_name = self._normalize_responses_model_name(self.config.llm_model_name)
        params = {
            "model": model_name,
            "input": input_payload,
            "temperature": self.config.llm_temperature,
            "top_p": self.config.llm_top_p,
            "max_output_tokens": self.config.llm_max_output_tokens,
            "timeout": self.config.llm_timeout,
        }
        if model_name.lower().startswith("openai/gpt-5") or "codex" in model_name.lower():
            reasoning_effort = None
            if isinstance(self.config.llm_additional_params, dict):
                reasoning_effort = self.config.llm_additional_params.get("reasoning_effort")
            if reasoning_effort != "none":
                params.pop("temperature", None)
                params.pop("top_p", None)
        if self.config.llm_api_key:
            params["api_key"] = self.config.llm_api_key
        if instructions:
            params["instructions"] = instructions
        if self.config.llm_base_url:
            params["base_url"] = self.config.llm_base_url
        if self.config.llm_api_version:
            params["api_version"] = self.config.llm_api_version
        if self.config.llm_custom_provider:
            params["custom_llm_provider"] = self.config.llm_custom_provider
        params.update(self.config.llm_additional_params)
        params.update(kwargs)

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        self._ensure_responses_json_trigger(params)
        return self._filter_responses_params(params)

    def _normalize_responses_model_name(self, model_name: Optional[str]) -> str:
        name = (model_name or "").strip()
        if not name:
            return model_name or ""
        if "/" in name:
            return name
        if self.config.llm_custom_provider:
            return name
        lower = name.lower()
        if lower.startswith("gpt-") or "codex" in lower:
            return f"openai/{name}"
        return name

    def _filter_supported_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        model_name = params.get("model")
        custom_provider = params.get("custom_llm_provider")
        supported = get_supported_openai_params(model_name, custom_provider)
        if not supported:
            return params

        supported_set = set(supported)
        if "max_output_tokens" in supported_set and "max_tokens" in params:
            params["max_output_tokens"] = params.pop("max_tokens")
        elif "max_completion_tokens" in supported_set and "max_tokens" in params:
            params["max_completion_tokens"] = params.pop("max_tokens")

        base_keys = {
            "model",
            "messages",
            "api_key",
            "base_url",
            "api_version",
            "timeout",
            "custom_llm_provider",
        }
        for key in list(params.keys()):
            if key in base_keys:
                continue
            if key not in supported_set:
                params.pop(key)
        return params

    def _filter_responses_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        allowed = self._responses_param_keys
        if not allowed:
            return params
        filtered = {k: v for k, v in params.items() if k in allowed}
        if params.get("api_key"):
            filtered["api_key"] = params["api_key"]
        if "input" not in filtered and "messages" in params:
            filtered["input"] = params["messages"]
        return filtered

    def _get_responses_param_keys(self) -> Optional[set]:
        try:
            import inspect
            return set(inspect.signature(llm_responses).parameters.keys())
        except Exception:
            return None

    def _use_responses_api(self, messages: List[Any], tools: List[Dict[str, Any]] = None) -> bool:
        """
        Determine whether to use the responses API or chat/completions API.

        Uses litellm's model info to detect the correct API, falling back to
        manual config if specified.
        """
        mode = (self.config.llm_api_mode or "auto").lower()

        # Explicit mode overrides auto-detection
        if mode == "responses":
            return True
        if mode in {"chat", "chat_completion", "completion"}:
            return False

        model = (self.config.llm_model_name or "").lower()
        if "codex" in model:
            return True
        if model.startswith("gpt-5-pro"):
            return True
        if model.startswith("gpt-5"):
            return False

        # Auto-detect using litellm's model info
        try:
            from litellm import get_model_info
            info = get_model_info(model)
            model_mode = info.get("mode", "chat")
            return model_mode == "responses"
        except Exception:
            return False

    def uses_responses_api(self) -> bool:
        """Public helper for upstream callers."""
        return self._use_responses_api([], None)

    def _update_last_response_id(self, response: Any) -> None:
        response_id = None
        if isinstance(response, dict):
            response_id = response.get("id")
        else:
            response_id = getattr(response, "id", None)
        if response_id:
            self.last_response_id = response_id

    def _normalize_responses_input(
        self, messages: List[Any]
    ) -> Tuple[Any, Optional[str]]:
        """
        Convert chat-style messages into Responses API input format.

        - System messages are extracted into `instructions`.
        - Message content is converted into content parts (input_text/output_text).
        """
        if isinstance(messages, str):
            return messages, None

        if not isinstance(messages, list):
            return messages, None

        instructions_parts: List[str] = []
        input_items: List[Dict[str, Any]] = []

        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role") or "user"
            content = msg.get("content")

            if role == "system":
                if isinstance(content, str) and content.strip():
                    instructions_parts.append(content.strip())
                continue

            content_parts: List[Dict[str, Any]] = []
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    part_type = part.get("type")
                    if part_type in {"input_text", "output_text", "input_image", "image_url"}:
                        content_parts.append(part)
                        continue
                    if part_type == "text":
                        text = part.get("text")
                        if text:
                            content_parts.append({"type": "input_text", "text": text})
                        continue
                    if part_type == "image_url":
                        image_url = part.get("image_url", {}).get("url") if isinstance(part.get("image_url"), dict) else part.get("image_url")
                        if image_url:
                            content_parts.append({"type": "input_image", "image_url": image_url})
                        continue
            elif isinstance(content, str):
                if role == "assistant":
                    content_parts.append({"type": "output_text", "text": content})
                else:
                    content_parts.append({"type": "input_text", "text": content})
            elif content is not None:
                text = str(content)
                if role == "assistant":
                    content_parts.append({"type": "output_text", "text": text})
                else:
                    content_parts.append({"type": "input_text", "text": text})

            if content_parts:
                input_items.append({"role": role, "content": content_parts})

        instructions = "\n\n".join(instructions_parts) if instructions_parts else None
        return input_items, instructions

    def _ensure_responses_json_trigger(self, params: Dict[str, Any]) -> None:
        """Ensure input contains 'json' when using Responses text.format json_object."""
        text_cfg = params.get("text")
        if not isinstance(text_cfg, dict):
            return
        fmt = text_cfg.get("format")
        if not (isinstance(fmt, dict) and fmt.get("type") == "json_object"):
            return

        input_payload = params.get("input")
        instructions = params.get("instructions")
        if self._input_contains_json(input_payload):
            return

        trigger_text = "Respond in JSON."

        if isinstance(instructions, str) and instructions.strip():
            if "json" not in instructions.lower():
                params["instructions"] = f"{instructions}\n\n{trigger_text}"
        else:
            params["instructions"] = trigger_text

        if isinstance(input_payload, list):
            input_payload.insert(
                0,
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": trigger_text}],
                },
            )
            return
        if isinstance(input_payload, str):
            params["input"] = f"{trigger_text}\n\n{input_payload}".strip()
            return
        if input_payload is None:
            params["input"] = trigger_text
            return

    def _input_contains_json(self, input_payload: Any) -> bool:
        if isinstance(input_payload, str):
            return "json" in input_payload.lower()
        if isinstance(input_payload, list):
            for item in input_payload:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        text = part.get("text")
                        if isinstance(text, str) and "json" in text.lower():
                            return True
                elif isinstance(content, str) and "json" in content.lower():
                    return True
        return False

    def _extract_message(
        self, response: Any
    ) -> Tuple[Optional[Any], List[Any], str]:
        """Extract message, tool calls, and content from a model response."""
        message = None
        tool_calls: List[Any] = []
        content = ""

        if hasattr(response, "choices"):
            choices = getattr(response, "choices") or []
            if choices:
                message = getattr(choices[0], "message", None)
                if message is None and hasattr(choices[0], "delta"):
                    message = choices[0].delta
            if message is not None:
                content = getattr(message, "content", None) or ""
                tool_calls = getattr(message, "tool_calls", None) or []
                return message, tool_calls, content

        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                msg = choices[0].get("message") or choices[0].get("delta") or {}
                content = msg.get("content") or ""
                tool_calls = msg.get("tool_calls") or []
                return msg, tool_calls, content
            output_text = response.get("output_text") or response.get("text") or response.get("content")
            if output_text:
                if isinstance(output_text, list):
                    output_text = "".join(str(item) for item in output_text)
                return None, [], str(output_text)
            output = response.get("output")
            if output:
                return None, [], self._extract_output_text(output)

        if isinstance(response, str):
            return None, [], response

        output_text = getattr(response, "output_text", None)
        if output_text:
            if isinstance(output_text, list):
                output_text = "".join(str(item) for item in output_text)
            return None, [], str(output_text)

        attr_content = getattr(response, "content", None)
        if attr_content:
            return None, [], str(attr_content)

        output_attr = getattr(response, "output", None)
        if output_attr:
            return None, [], self._extract_output_text(output_attr)

        return None, [], ""

    def _extract_stream_delta(
        self,
        response: Any,
        *,
        response_type: Optional[str] = None,
        has_accumulated: bool = False,
    ) -> Tuple[Optional[str], Optional[List[Any]]]:
        """Extract delta content and tool calls from a streaming response chunk."""
        if response_type and str(response_type).endswith(".done"):
            done_text = None
            if isinstance(response, dict):
                done_text = response.get("text")
            else:
                done_text = getattr(response, "text", None)
            if done_text and not has_accumulated:
                return done_text, None
            return None, None
        if hasattr(response, "choices"):
            choices = getattr(response, "choices") or []
            if choices and hasattr(choices[0], "delta"):
                delta = choices[0].delta
                delta_content = getattr(delta, "content", None)
                delta_tool_calls = getattr(delta, "tool_calls", None)
                return delta_content, delta_tool_calls

        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                return delta.get("content"), delta.get("tool_calls")
            response_type = response.get("type", "")
            if response_type.endswith(".done"):
                if has_accumulated:
                    return None, None
                if "text" in response:
                    return response.get("text"), None
            if response_type.endswith(".delta") and "delta" in response:
                return response.get("delta"), None
            if "text" in response:
                return response.get("text"), None
            if "delta" in response:
                return response.get("delta"), None

        if isinstance(response, str):
            return response, None

        delta_attr = getattr(response, "delta", None)
        if delta_attr:
            return delta_attr, None

        text_attr = getattr(response, "text", None)
        if text_attr:
            return text_attr, None

        type_attr = getattr(response, "type", None)
        if type_attr and str(type_attr).endswith(".delta"):
            delta_val = getattr(response, "delta", None)
            if delta_val:
                return delta_val, None
        if type_attr and str(type_attr).endswith(".done"):
            done_text = getattr(response, "text", None)
            if done_text and not has_accumulated:
                return done_text, None

        return None, None

    def _extract_output_text(self, output: Any) -> str:
        """Extract text from responses-style output payloads."""
        texts: List[str] = []

        if isinstance(output, list):
            for item in output:
                extracted = self._extract_output_text(item)
                if extracted:
                    return extracted
            return ""

        if isinstance(output, dict):
            content = output.get("content")
            if content:
                extracted = self._extract_output_text(content)
                if extracted:
                    return extracted
            text = output.get("text")
            if text:
                return str(text)
            return ""

        content_attr = getattr(output, "content", None)
        if content_attr:
            return self._extract_output_text(content_attr)

        text_attr = getattr(output, "text", None)
        if text_attr:
            return str(text_attr)

        return ""

    def _extract_usage(self, response: Any) -> Dict[str, Any]:
        """Extract usage metrics from response, handling both dict and object forms."""
        usage = getattr(response, "usage", None) if not isinstance(response, dict) else response.get("usage")
        if usage is None:
            return {}
        if isinstance(usage, dict):
            return usage
        # Handle object-style usage (ResponseAPIUsage or similar)
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            "cost": getattr(usage, "cost", 0.0) or 0.0,
        }

    def _update_metrics(self, response: Any, log: bool = False) -> None:
        """Update internal metrics from response usage."""
        usage = self._extract_usage(response)
        prompt_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
        cost = usage.get("cost", 0.0) or 0.0
        self.metrics.add_tokens(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        self.metrics.add_cost(cost)
        if log:
            self.logger.info(f"Tokens: {self.metrics.total_tokens}, Cost: ${self.metrics.total_cost:.4f}")

    def __call__(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        use_async = kwargs.pop("use_async", None)
        if use_async is None:
            use_async = self.config.llm_use_async

        stream = kwargs.get("stream")
        if stream is None:
            stream = self.config.llm_stream
            kwargs["stream"] = stream

        if use_async:
            if stream:
                return self.stream_generate(messages, tools=tools, **kwargs)
            return self.agenerate(messages, tools=tools, **kwargs)

        if stream:
            # OpenAI's API does not support synchronous streaming; streaming must be async
            raise NotImplementedError("Synchronous streaming is not supported.")
        return self.generate(messages, tools=tools, **kwargs)
