"""
Responses API Handler.

Handles the OpenAI Responses API format (used by gpt-5-codex and similar models).
"""

import inspect
import json
from typing import Any, Dict, List, Optional, Tuple

from litellm import (
    aresponses as llm_aresponses,
    responses as llm_responses,
)

from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.api_handlers.base import BaseHandler
from aeiva.llm.tool_types import ToolCall, ToolCallDelta


class ResponsesAPIHandler(BaseHandler):
    """
    Handler for OpenAI Responses API.

    Used by: gpt-5-codex, gpt-5.1-codex, gpt-5-pro, etc.
    """

    def __init__(self, config: LLMGatewayConfig):
        super().__init__(config)
        self._allowed_params = self._get_allowed_params()

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
            matched = [t for t in (tools or []) if t.get("name") == target]
            if not matched:
                raise ValueError(f"tool_choice requested unknown tool: {target}")
            return matched, tool_choice, f"You must call the {target} tool before responding."

        return tools, tool_choice, None


    def _get_allowed_params(self) -> Optional[set]:
        """Get allowed parameters for responses API."""
        try:
            return set(inspect.signature(llm_responses).parameters.keys())
        except (TypeError, ValueError):
            return None

    def build_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build responses API parameters."""
        input_payload, instructions = self._normalize_input(messages)
        model_name = self._normalize_model_name(self.config.llm_model_name)

        tool_choice = kwargs.pop("tool_choice", None)
        if tool_choice is None:
            tool_choice = getattr(self.config, "llm_tool_choice", None)

        params = {
            "model": model_name,
            "input": input_payload,
            "temperature": self.config.llm_temperature,
            "top_p": self.config.llm_top_p,
            "max_output_tokens": self.config.llm_max_output_tokens,
            "timeout": self.config.llm_timeout,
        }

        # Some models don't support temperature/top_p
        if self._should_drop_sampling_params(model_name):
            params.pop("temperature", None)
            params.pop("top_p", None)

        self._add_auth_params(params)
        self._add_additional_params(params, **kwargs)

        normalized_tools = self._normalize_tools(tools) if tools else None
        normalized_tools, resolved_choice, extra_prompt = self._resolve_tool_choice(
            normalized_tools, tool_choice
        )

        if extra_prompt:
            if instructions:
                instructions = f"{instructions}\n\n{extra_prompt}"
            else:
                instructions = extra_prompt

        if normalized_tools:
            params["tools"] = normalized_tools
            if resolved_choice is not None:
                params["tool_choice"] = resolved_choice

        if instructions:
            params["instructions"] = instructions

        self._ensure_json_trigger(params)
        return self._filter_params(params)

    def _normalize_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize tool schemas to Responses API format."""
        normalized: List[Dict[str, Any]] = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            if "function" in tool:
                func = tool.get("function") or {}
                item = {
                    "type": tool.get("type", "function"),
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "parameters": func.get("parameters"),
                }
            else:
                item = dict(tool)
            if not item.get("name"):
                continue
            normalized.append(item)
        return normalized

    def _should_drop_sampling_params(self, model_name: str) -> bool:
        """Check if model doesn't support temperature/top_p."""
        lower = model_name.lower()
        if "gpt-5" in lower or "codex" in lower:
            reasoning_effort = None
            if isinstance(self.config.llm_additional_params, dict):
                reasoning_effort = self.config.llm_additional_params.get("reasoning_effort")
            if reasoning_effort != "none":
                return True
        return False

    def _normalize_model_name(self, model_name: Optional[str]) -> str:
        """Normalize model name for responses API (add openai/ prefix if needed)."""
        name = (model_name or "").strip()
        if not name:
            return name

        # Already has provider prefix
        if "/" in name:
            return name

        # Has custom provider configured
        if self.config.llm_custom_provider:
            return name

        # Add openai/ prefix for GPT models
        lower = name.lower()
        if lower.startswith("gpt-") or "codex" in lower:
            return f"openai/{name}"

        return name

    def _normalize_input(
        self,
        messages: List[Any],
    ) -> Tuple[Any, Optional[str]]:
        """
        Convert chat-style messages into Responses API input format.

        System messages become instructions, other messages become input items.
        Tool messages are converted to function_call/function_call_output format.
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

            # System messages become instructions
            if role == "system":
                if isinstance(content, str) and content.strip():
                    instructions_parts.append(content.strip())
                continue

            # Handle assistant messages with tool_calls (convert to function_call items)
            tool_calls = msg.get("tool_calls")
            if role == "assistant" and tool_calls:
                # Add content if present
                if content:
                    content_parts = self._convert_content(content, role)
                    if content_parts:
                        input_items.append({"role": role, "content": content_parts})

                # Convert each tool_call to function_call format
                for tc in tool_calls:
                    if isinstance(tc, ToolCall):
                        call_id = tc.id or ""
                        name = tc.name or ""
                        arguments = tc.arguments or "{}"
                    elif isinstance(tc, dict):
                        func = tc.get("function") or {}
                        call_id = tc.get("id") or ""
                        name = func.get("name") or ""
                        arguments = func.get("arguments") or "{}"
                    else:
                        call_id = getattr(tc, "id", "") or ""
                        func = getattr(tc, "function", None)
                        if func:
                            name = getattr(func, "name", "") or ""
                            arguments = getattr(func, "arguments", "{}") or "{}"
                        else:
                            continue

                    if name:
                        input_items.append({
                            "type": "function_call",
                            "call_id": call_id,
                            "name": name,
                            "arguments": arguments,
                        })
                continue

            # Handle tool role messages (convert to function_call_output)
            if role == "tool":
                call_id = msg.get("tool_call_id") or ""
                output = content if isinstance(content, str) else json.dumps(content) if content else ""
                input_items.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": output,
                })
                continue

            # Convert regular content to input format
            content_parts = self._convert_content(content, role)
            if content_parts:
                input_items.append({"role": role, "content": content_parts})

        instructions = "\n\n".join(instructions_parts) if instructions_parts else None
        return input_items, instructions

    def _convert_content(
        self,
        content: Any,
        role: str,
    ) -> List[Dict[str, Any]]:
        """Convert message content to Responses API format."""
        content_parts: List[Dict[str, Any]] = []

        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_type = part.get("type")

                # Already in correct format
                if part_type in {"input_text", "output_text", "input_image"}:
                    content_parts.append(part)
                    continue

                # Convert text
                if part_type == "text":
                    text = part.get("text")
                    if text:
                        content_parts.append({"type": "input_text", "text": text})
                    continue

                # Convert image_url
                if part_type == "image_url":
                    image_url = part.get("image_url")
                    if isinstance(image_url, dict):
                        url = image_url.get("url")
                    else:
                        url = image_url
                    if url:
                        content_parts.append({"type": "input_image", "image_url": url})
                    continue

        elif isinstance(content, str):
            text_type = "output_text" if role == "assistant" else "input_text"
            content_parts.append({"type": text_type, "text": content})

        elif content is not None:
            text = str(content)
            text_type = "output_text" if role == "assistant" else "input_text"
            content_parts.append({"type": text_type, "text": text})

        return content_parts

    def _ensure_json_trigger(self, params: Dict[str, Any]) -> None:
        """Ensure input contains 'json' when using json_object format."""
        text_cfg = params.get("text")
        if not isinstance(text_cfg, dict):
            return

        fmt = text_cfg.get("format")
        if not (isinstance(fmt, dict) and fmt.get("type") == "json_object"):
            return

        # Check if input already contains 'json'
        if self._input_contains_json(params.get("input"), params.get("instructions")):
            return

        trigger_text = "Respond in JSON."

        # Add to instructions
        instructions = params.get("instructions")
        if isinstance(instructions, str) and instructions.strip():
            if "json" not in instructions.lower():
                params["instructions"] = f"{instructions}\n\n{trigger_text}"
        else:
            params["instructions"] = trigger_text

        # Also add to input for safety
        input_payload = params.get("input")
        if isinstance(input_payload, list):
            input_payload.insert(0, {
                "role": "system",
                "content": [{"type": "input_text", "text": trigger_text}],
            })
        elif isinstance(input_payload, str):
            params["input"] = f"{trigger_text}\n\n{input_payload}".strip()
        elif input_payload is None:
            params["input"] = trigger_text

    def _input_contains_json(
        self,
        input_payload: Any,
        instructions: Optional[str],
    ) -> bool:
        """Check if input or instructions contain 'json'."""
        if isinstance(instructions, str) and "json" in instructions.lower():
            return True

        if isinstance(input_payload, str):
            return "json" in input_payload.lower()

        if isinstance(input_payload, list):
            for item in input_payload:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            text = part.get("text")
                            if isinstance(text, str) and "json" in text.lower():
                                return True
                elif isinstance(content, str) and "json" in content.lower():
                    return True

        return False

    def _filter_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Filter to only allowed parameters for responses API."""
        if not self._allowed_params:
            return params

        filtered = {k: v for k, v in params.items() if k in self._allowed_params}

        # Always keep api_key
        if params.get("api_key"):
            filtered["api_key"] = params["api_key"]

        # Ensure input is present
        if "input" not in filtered and "messages" in params:
            filtered["input"] = params["messages"]

        return filtered

    def parse_response(
        self,
        response: Any,
    ) -> Tuple[Optional[Any], List[ToolCall], str]:
        """Parse responses API response.

        Returns:
            Tuple of (message, tool_calls, content_text)
            - tool_calls are normalized to Chat API format for compatibility
        """
        # Get output array (may contain text and function_calls)
        output = None
        if isinstance(response, dict):
            output = response.get("output")
        else:
            output = getattr(response, "output", None)

        # Extract function calls from output array
        tool_calls = self._extract_function_calls(output)

        # Try output_text attribute (fast path)
        output_text = getattr(response, "output_text", None)
        if output_text:
            if isinstance(output_text, list):
                output_text = "".join(str(item) for item in output_text)
            return None, tool_calls, str(output_text)

        # Try dict format
        if isinstance(response, dict):
            output_text = response.get("output_text") or response.get("text") or response.get("content")
            if output_text:
                if isinstance(output_text, list):
                    output_text = "".join(str(item) for item in output_text)
                return None, tool_calls, str(output_text)

            # Try output array for text
            if output:
                return None, tool_calls, self._extract_output_text(output)

        # Try content attribute
        content = getattr(response, "content", None)
        if content:
            return None, tool_calls, str(content)

        # Try output attribute for text
        if output:
            return None, tool_calls, self._extract_output_text(output)

        # Handle string
        if isinstance(response, str):
            return None, tool_calls, response

        return None, tool_calls, ""

    def _extract_function_calls(self, output: Any) -> List[Dict[str, Any]]:
        """Extract tool call items from output and convert to Chat API format.

        Responses API format:
            {"type": "function_call", "call_id": "...", "name": "...", "arguments": "..."}
            {"type": "tool_call", "call_id": "...", "name": "...", "arguments": "..."}

        Chat API format (returned):
            {"id": "...", "type": "function", "function": {"name": "...", "arguments": "..."}}
        """
        tool_calls: List[ToolCall] = []

        if not output:
            return tool_calls

        if not isinstance(output, list):
            output = [output]

        for item in output:
            # Convert to dict if needed
            if not isinstance(item, dict) and hasattr(item, "model_dump"):
                item = item.model_dump()
            elif not isinstance(item, dict):
                item_type = getattr(item, "type", None)
                if item_type == "function_call":
                    item = {
                        "type": "function_call",
                        "call_id": getattr(item, "call_id", None) or getattr(item, "id", None),
                        "name": getattr(item, "name", None),
                        "arguments": getattr(item, "arguments", None),
                    }
                else:
                    continue

            if not isinstance(item, dict):
                continue

            item_type = item.get("type")
            if item_type in {"function_call", "tool_call", "custom_tool_call"} or (
                item_type is None and item.get("name") and item.get("arguments") is not None
            ):
                call_id = item.get("call_id") or item.get("id") or ""
                name = item.get("name") or ""
                arguments = item.get("arguments") or "{}"

                if name:  # Only add if we have a function name
                    # Convert to Chat API format for compatibility with _parse_tool_call
                    tool_call = ToolCall(
                        id=str(call_id),
                        name=str(name),
                        arguments=arguments if isinstance(arguments, str) else json.dumps(arguments),
                    )
                    tool_calls.append(tool_call)

        return tool_calls

    def _extract_output_text(self, output: Any) -> str:
        """Extract text from responses-style output payloads."""
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

        # Try attributes
        content_attr = getattr(output, "content", None)
        if content_attr:
            return self._extract_output_text(content_attr)

        text_attr = getattr(output, "text", None)
        if text_attr:
            return str(text_attr)

        return ""

    def parse_stream_delta(
        self,
        chunk: Any,
        response_type: Optional[str] = None,
        has_accumulated: bool = False,
        **kwargs,
    ) -> Tuple[Optional[str], Optional[List[ToolCallDelta]]]:
        """Parse streaming chunk from responses API."""
        # Get response type
        if response_type is None:
            response_type = getattr(chunk, "type", None)
            if response_type is None and isinstance(chunk, dict):
                response_type = chunk.get("type", "")

        if hasattr(response_type, "value"):
            response_type = getattr(response_type, "value")
        response_type = str(response_type) if response_type else ""

        def _get_output_index(payload: Any) -> Optional[int]:
            if isinstance(payload, dict):
                idx = payload.get("output_index")
            else:
                idx = getattr(payload, "output_index", None)
            return int(idx) if idx is not None else None

        # Handle function-call argument streaming (prefer the .done event)
        if response_type.startswith("response.function_call_arguments."):
            if response_type.endswith(".done"):
                payload = chunk if isinstance(chunk, dict) else getattr(chunk, "__dict__", {})
                call_id = payload.get("call_id") or payload.get("id")
                name = payload.get("name")
                arguments = payload.get("arguments")
                delta = ToolCallDelta.from_any({
                    "id": call_id,
                    "name": name,
                    "arguments": arguments,
                    "index": _get_output_index(payload) or 0,
                })
                return None, [delta] if delta else None
            # Ignore partial argument deltas to avoid incomplete JSON
            return None, None

        # Ignore custom tool input streaming for now (handled via completed response)
        if response_type.startswith("response.custom_tool_call_input."):
            return None, None

        # Handle output item events (tool calls)
        if response_type.endswith("output_item.added") or response_type.endswith("output_item.delta"):
            item = None
            if isinstance(chunk, dict):
                item = chunk.get("item") or chunk.get("delta")
            else:
                item = getattr(chunk, "item", None) or getattr(chunk, "delta", None)

            if item:
                if not isinstance(item, dict) and hasattr(item, "model_dump"):
                    item = item.model_dump()

                if isinstance(item, dict) and item.get("type") == "function_call":
                    delta = ToolCallDelta.from_any({
                        "id": item.get("call_id") or item.get("id"),
                        "name": item.get("name"),
                        "arguments": item.get("arguments"),
                        "index": _get_output_index(chunk) or 0,
                    })
                    return None, [delta] if delta else None

            return None, None

        # Handle .done events
        if response_type.endswith(".done"):
            if has_accumulated:
                return None, None
            done_text = None
            if isinstance(chunk, dict):
                done_text = chunk.get("text")
            else:
                done_text = getattr(chunk, "text", None)
            return done_text, None

        # Handle .delta events
        if response_type.endswith(".delta"):
            delta = None
            if isinstance(chunk, dict):
                delta = chunk.get("delta")
            else:
                delta = getattr(chunk, "delta", None)

            if isinstance(delta, dict):
                if delta.get("type") in {"function_call", "tool_call"}:
                    tool_delta = ToolCallDelta.from_any(delta)
                    return None, [tool_delta] if tool_delta else None
                if any(key in delta for key in ("name", "arguments", "call_id", "id")):
                    tool_delta = ToolCallDelta.from_any(delta)
                    return None, [tool_delta] if tool_delta else None

            return delta, None

        # Handle text attribute
        if isinstance(chunk, dict):
            if "text" in chunk:
                return chunk.get("text"), None
            if "delta" in chunk:
                return chunk.get("delta"), None

        # Handle string
        if isinstance(chunk, str):
            return chunk, None

        # Try attributes
        delta_attr = getattr(chunk, "delta", None)
        if delta_attr:
            return delta_attr, None

        text_attr = getattr(chunk, "text", None)
        if text_attr:
            return text_attr, None

        return None, None

    async def execute(
        self,
        params: Dict[str, Any],
        stream: bool = False,
    ) -> Any:
        """Execute responses API call."""
        params["stream"] = stream
        return await self._execute_with_fallback(llm_aresponses, params)

    def execute_sync(
        self,
        params: Dict[str, Any],
    ) -> Any:
        """Execute responses API call synchronously."""
        params["stream"] = False
        return self._execute_with_fallback_sync(llm_responses, params)
