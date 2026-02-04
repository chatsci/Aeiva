"""
LLM Client - Unified interface for language model interactions.

Supports synchronous, asynchronous, and streaming modes with optional tool usage.
Uses the Strategy pattern to handle different API formats (chat/completions vs responses).
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import litellm

from aeiva.llm.patches import apply_all_patches
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.llm_gateway_exceptions import LLMGatewayError, llm_gateway_exception
from aeiva.llm.fault_tolerance import retry_async, retry_sync
from aeiva.llm.llm_usage_metrics import LLMUsageMetrics
from aeiva.llm.api_handlers import ChatAPIHandler, ResponsesAPIHandler, LLMHandler
from aeiva.tool.registry import get_registry

# Apply patches for third-party library issues
apply_all_patches()
litellm.drop_params = True


# =============================================================================
# Model → API Type Registry
# =============================================================================

MODEL_API_REGISTRY: Dict[str, str] = {
    # Responses API models
    "codex": "responses",
    "gpt-5-pro": "responses",
    "gpt-5.1-pro": "responses",
    "gpt-5.2-pro": "responses",
    # Chat API models
    "gpt-5": "chat",
    "gpt-4": "chat",
    "gpt-3.5": "chat",
    "o1-": "chat",
    "o3-": "chat",
}


def _detect_api_type(model_name: str) -> Optional[str]:
    """Detect API type from model name. Returns 'responses', 'chat', or None."""
    if not model_name:
        return None
    lower = model_name.lower()
    for pattern, api_type in sorted(MODEL_API_REGISTRY.items(), key=lambda x: -len(x[0])):
        if pattern in lower:
            return api_type
    return None


# =============================================================================
# Streaming Result
# =============================================================================

@dataclass
class StreamResult:
    """Result from a single streaming iteration."""
    content: str
    has_tool_calls: bool
    completed_response: Any = None


# =============================================================================
# LLM Client
# =============================================================================

class LLMClient:
    """
    Unified LLM interface supporting sync, async, and streaming modes.

    Uses Strategy pattern to handle different API formats (chat vs responses).
    """

    # Default max tool call iterations (can be overridden via config)
    DEFAULT_MAX_TOOL_LOOPS = 10

    def __init__(self, config: LLMGatewayConfig):
        self.config = config
        self.metrics = LLMUsageMetrics()
        self.logger = logging.getLogger(__name__)
        self.last_response_id: Optional[str] = None
        self._handler: Optional[LLMHandler] = None

        if not self.config.llm_api_key:
            raise ValueError("API key must be provided in the configuration.")

        self._configure_litellm()

    @property
    def max_tool_loops(self) -> int:
        """Maximum tool call iterations before giving up."""
        return getattr(self.config, 'llm_max_tool_loops', self.DEFAULT_MAX_TOOL_LOOPS)

    def _configure_litellm(self) -> None:
        """Configure global litellm settings."""
        if hasattr(litellm, "suppress_debug_info"):
            litellm.suppress_debug_info = True
        if self.config.llm_api_key:
            litellm.api_key = self.config.llm_api_key
            litellm.openai_key = self.config.llm_api_key

    def _get_handler(self) -> LLMHandler:
        """Get the appropriate strategy for the current model."""
        if self._handler is None:
            self._handler = (
                ResponsesAPIHandler(self.config)
                if self.uses_responses_api()
                else ChatAPIHandler(self.config)
            )
        return self._handler

    def uses_responses_api(self) -> bool:
        """Determine whether to use the responses API."""
        mode = (self.config.llm_api_mode or "auto").lower()

        if mode == "responses":
            return True
        if mode in {"chat", "chat_completion", "completion"}:
            return False

        model = self.config.llm_model_name or ""
        api_type = _detect_api_type(model)
        if api_type:
            return api_type == "responses"

        try:
            from litellm import get_model_info
            return get_model_info(model.lower()).get("mode") == "responses"
        except Exception:
            return False

    # =========================================================================
    # Synchronous Generation
    # =========================================================================

    @retry_sync(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),
    )
    def generate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> str:
        """Synchronous generation with optional tool calling."""
        try:
            strategy = self._get_handler()

            for _ in range(self.max_tool_loops):
                params = strategy.build_params(messages, tools, **kwargs)
                response = strategy.execute_sync(params)
                self._update_metrics(response)
                _, tool_calls, content = strategy.parse_response(response)

                if tool_calls:
                    self._execute_tool_calls_sync(messages, tool_calls)
                    continue

                self._update_last_response_id(response)
                messages.append({"role": "assistant", "content": content})
                return content

            raise Exception("Maximum tool call iterations reached.")

        except Exception as e:
            self.logger.error(f"Generation error: {e}")
            raise llm_gateway_exception(e)

    # =========================================================================
    # Asynchronous Generation
    # =========================================================================

    @retry_async(
        max_attempts=lambda self: self.config.llm_num_retries,
        backoff_factor=lambda self: self.config.llm_retry_backoff_factor,
        exceptions=(LLMGatewayError,),
    )
    async def agenerate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> str:
        """Asynchronous generation with optional tool calling."""
        try:
            strategy = self._get_handler()

            for _ in range(self.max_tool_loops):
                params = strategy.build_params(messages, tools, **kwargs)
                response = await strategy.execute(params, stream=False)
                self._update_metrics(response)
                _, tool_calls, content = strategy.parse_response(response)

                if tool_calls:
                    await self._execute_tool_calls_async(messages, tool_calls)
                    continue

                self._update_last_response_id(response)
                messages.append({"role": "assistant", "content": content})
                return content

            raise Exception("Maximum tool call iterations reached.")

        except Exception as e:
            self.logger.error(f"Async generation error: {e}")
            raise llm_gateway_exception(e)

    # =========================================================================
    # Streaming Generation
    # =========================================================================

    async def stream_generate(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        """Streaming generation with optional tool calling."""
        try:
            if not kwargs.get("stream", self.config.llm_stream):
                response = await self.agenerate(messages, tools=tools, stream=False)
                if response:
                    yield response
                return

            strategy = self._get_handler()

            for _ in range(self.max_tool_loops):
                result = await self._stream_once(strategy, messages, tools, **kwargs)

                # Yield accumulated content
                if result.content:
                    yield result.content

                # Continue if tool calls were made, else we're done
                if not result.has_tool_calls:
                    return

            yield "Maximum tool call iterations reached."

        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            try:
                response = await self.agenerate(messages, tools=tools, stream=False)
                if response:
                    yield response
                    return
            except Exception:
                pass
            yield f"Streaming error: {e}"

    async def _stream_once(
        self,
        strategy: LLMHandler,
        messages: List[Any],
        tools: Optional[List[Dict[str, Any]]],
        **kwargs,
    ) -> StreamResult:
        """Execute one streaming iteration, collecting all chunks."""
        params = strategy.build_params(messages, tools, **kwargs)
        response_stream = await strategy.execute(params, stream=True)

        tool_calls: List[Dict[str, Any]] = []
        chunks: List[str] = []
        completed_response = None

        async for chunk in response_stream:
            response_type = getattr(chunk, "type", None)

            if response_type and str(response_type).endswith("response.completed"):
                completed_response = getattr(chunk, "response", None)

            delta_content, delta_tool_calls = strategy.parse_stream_delta(
                chunk, response_type=response_type, has_accumulated=bool(chunks)
            )

            if delta_content:
                chunks.append(delta_content)

            if delta_tool_calls:
                self._accumulate_tool_calls(tool_calls, delta_tool_calls)

        # Build final content (handle cumulative vs incremental deltas)
        full_content = self._merge_chunks(chunks)

        # Handle tool calls
        if tool_calls:
            await self._execute_tool_calls_async(messages, tool_calls, available_tools=tools)
            return StreamResult(content="", has_tool_calls=True)

        # No tool calls - finalize
        if not full_content and completed_response:
            _, _, text = strategy.parse_response(completed_response)
            full_content = text or ""

        if completed_response:
            self._update_metrics(completed_response)
            self._update_last_response_id(completed_response)

        messages.append({"role": "assistant", "content": full_content})
        return StreamResult(content=full_content, has_tool_calls=False, completed_response=completed_response)

    def _merge_chunks(self, chunks: List[str]) -> str:
        """Merge streaming chunks, handling cumulative vs incremental content."""
        if not chunks:
            return ""
        if len(chunks) == 1:
            return chunks[0]

        # Check if chunks are cumulative (each contains all previous content)
        result = chunks[0]
        for chunk in chunks[1:]:
            if chunk.startswith(result):
                result = chunk  # Cumulative: take the longer one
            else:
                result += chunk  # Incremental: concatenate
        return result

    def _accumulate_tool_calls(
        self, tool_calls: List[Dict[str, Any]], deltas: List[Any]
    ) -> None:
        """Accumulate streaming tool call chunks."""
        for chunk in deltas:
            index = getattr(chunk, "index", None) or len(tool_calls)

            while len(tool_calls) <= index:
                tool_calls.append({
                    "id": "", "type": "function",
                    "function": {"name": "", "arguments": ""}
                })

            tc = tool_calls[index]
            if chunk_id := getattr(chunk, "id", None):
                tc["id"] += chunk_id
            if func := getattr(chunk, "function", None):
                if name := getattr(func, "name", None):
                    tc["function"]["name"] += name
                if args := getattr(func, "arguments", None):
                    tc["function"]["arguments"] += args

    # =========================================================================
    # Tool Execution
    # =========================================================================

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool via the registry."""
        return await get_registry().execute(tool_name, **params)

    def call_tool_sync(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute a tool synchronously via the registry."""
        return get_registry().execute_sync(tool_name, **params)

    def _execute_tool_calls_sync(self, messages: List[Any], tool_calls: List[Any]) -> None:
        """Execute tool calls synchronously."""
        messages.append({"role": "assistant", "tool_calls": tool_calls})

        for tool_call in tool_calls:
            name, args, call_id = self._parse_tool_call(tool_call)
            try:
                result = self.call_tool_sync(name, args)
            except Exception as e:
                self.logger.error(f"Tool '{name}' error: {e}")
                result = f"Error: {e}"

            messages.append({
                "tool_call_id": call_id, "role": "tool",
                "name": name, "content": str(result),
            })

    async def _execute_tool_calls_async(
        self,
        messages: List[Any],
        tool_calls: List[Any],
        *,
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Execute tool calls asynchronously."""
        messages.append({"role": "assistant", "tool_calls": tool_calls})

        available_names = (
            {t["function"]["name"] for t in available_tools if "function" in t}
            if available_tools else None
        )

        for tool_call in tool_calls:
            name, args, call_id = self._parse_tool_call(tool_call)

            if available_names and name not in available_names:
                self.logger.error(f"Unknown tool: {name}")
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = await self.call_tool(name, args)
                except Exception as e:
                    self.logger.error(f"Tool '{name}' error: {e}")
                    result = f"Error: {e}"

            messages.append({
                "tool_call_id": call_id, "role": "tool",
                "name": name, "content": str(result),
            })

    def _parse_tool_call(self, tool_call: Any) -> Tuple[str, Dict[str, Any], str]:
        """Parse tool call into (name, args, id)."""
        if isinstance(tool_call, dict):
            func = tool_call.get("function") or {}
            name, args_str, call_id = func.get("name", ""), func.get("arguments", "{}"), tool_call.get("id", "")
        else:
            name, args_str, call_id = tool_call.function.name, tool_call.function.arguments, tool_call.id

        try:
            args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
        except json.JSONDecodeError:
            args = {}

        return name, args, call_id

    # =========================================================================
    # Metrics & Utilities
    # =========================================================================

    def _update_last_response_id(self, response: Any) -> None:
        """Track the last response ID."""
        self.last_response_id = (
            response.get("id") if isinstance(response, dict)
            else getattr(response, "id", None)
        )

    def _extract_usage(self, response: Any) -> Dict[str, Any]:
        """Extract usage metrics from response."""
        usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        if not usage:
            return {}
        if isinstance(usage, dict):
            return usage
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        }

    def _update_metrics(self, response: Any) -> None:
        """Update internal metrics from response."""
        usage = self._extract_usage(response)
        self.metrics.add_tokens(
            prompt_tokens=usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0,
        )

    def __call__(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        """Main entry point - routes to appropriate generation method."""
        use_async = kwargs.pop("use_async", self.config.llm_use_async)
        stream = kwargs.setdefault("stream", self.config.llm_stream)

        if use_async:
            return self.stream_generate(messages, tools=tools, **kwargs) if stream else self.agenerate(messages, tools=tools, **kwargs)

        if stream:
            raise NotImplementedError("Synchronous streaming is not supported.")
        return self.generate(messages, tools=tools, **kwargs)
