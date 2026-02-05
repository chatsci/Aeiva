from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from aeiva.llm.backend import LLMBackend, LLMResponse
from aeiva.llm.llm_usage_metrics import LLMUsageMetrics
from aeiva.llm.tool_types import ToolCall, ToolCallDelta
from aeiva.tool.registry import get_registry


@dataclass
class ToolLoopResult:
    text: str
    usage: Dict[str, Any]
    response_id: Optional[str]
    raw: Any = None


@dataclass
class ToolLoopStreamResult:
    content: str
    has_tool_calls: bool
    usage: Dict[str, Any]
    response_id: Optional[str]
    completed_response: Any = None


class ToolLoopEngine:
    def __init__(
        self,
        backend: LLMBackend,
        metrics: Optional[LLMUsageMetrics] = None,
        max_tool_loops: int = 10,
        registry=None,
    ) -> None:
        self.backend = backend
        self.metrics = metrics
        self.max_tool_loops = max_tool_loops
        self.registry = registry or get_registry()
        self.last_response_id: Optional[str] = None

    def run(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> ToolLoopResult:
        for _ in range(self.max_tool_loops):
            params = self.backend.build_params(messages, tools, **kwargs)
            response = self.backend.execute_sync(params)
            parsed = self.backend.parse_response(response)

            if parsed.tool_calls:
                self._execute_tool_calls_sync(messages, parsed.tool_calls, tools)
                continue

            self._record_usage(parsed)
            self._update_last_response_id(parsed)
            messages.append({"role": "assistant", "content": parsed.text})
            return ToolLoopResult(parsed.text, parsed.usage, parsed.response_id, parsed.raw)

        raise RuntimeError("Maximum tool call iterations reached.")

    async def arun(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> ToolLoopResult:
        for _ in range(self.max_tool_loops):
            params = self.backend.build_params(messages, tools, **kwargs)
            response = await self.backend.execute(params, stream=False)
            parsed = self.backend.parse_response(response)

            if parsed.tool_calls:
                await self._execute_tool_calls_async(messages, parsed.tool_calls, tools)
                continue

            self._record_usage(parsed)
            self._update_last_response_id(parsed)
            messages.append({"role": "assistant", "content": parsed.text})
            return ToolLoopResult(parsed.text, parsed.usage, parsed.response_id, parsed.raw)

        raise RuntimeError("Maximum tool call iterations reached.")

    async def astream(
        self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        if not kwargs.get("stream", True):
            result = await self.arun(messages, tools=tools, stream=False, **kwargs)
            if result.text:
                yield result.text
            return

        for _ in range(self.max_tool_loops):
            stream_result = await self._stream_once(messages, tools, **kwargs)
            if stream_result.content:
                yield stream_result.content
            if not stream_result.has_tool_calls:
                return

        yield "Maximum tool call iterations reached."

    async def _stream_once(
        self,
        messages: List[Any],
        tools: Optional[List[Dict[str, Any]]],
        **kwargs,
    ) -> ToolLoopStreamResult:
        params = self.backend.build_params(messages, tools, **kwargs)
        response_stream = await self.backend.execute(params, stream=True)

        tool_calls: List[ToolCall] = []
        chunks: List[str] = []
        deferred_chunks: List[str] = []
        completed_response = None
        last_chunk: Any = None
        uses_responses = getattr(self.backend, "uses_responses_api", None)
        ignore_delta_content = bool(tools) and bool(uses_responses() if callable(uses_responses) else False)

        async for chunk in response_stream:
            last_chunk = chunk
            response_type = getattr(chunk, "type", None)
            if response_type and str(response_type).endswith("response.completed"):
                completed_response = getattr(chunk, "response", None)

            delta_content, delta_tool_calls = self.backend.parse_stream_delta(
                chunk, response_type=response_type, has_accumulated=bool(chunks)
            )

            if delta_content:
                if ignore_delta_content:
                    deferred_chunks.append(delta_content)
                else:
                    chunks.append(delta_content)
            if delta_tool_calls:
                self._accumulate_tool_calls(tool_calls, delta_tool_calls)

        full_content = self._merge_chunks(chunks)
        deferred_content = self._merge_chunks(deferred_chunks)

        if completed_response is None and last_chunk is not None:
            if isinstance(last_chunk, dict) and (last_chunk.get("output") or last_chunk.get("output_text")):
                completed_response = last_chunk
            elif hasattr(last_chunk, "output") or hasattr(last_chunk, "output_text"):
                completed_response = last_chunk

        parsed: Optional[LLMResponse] = None
        if completed_response is not None:
            parsed = self.backend.parse_response(completed_response)
            self._record_usage(parsed)
            self._update_last_response_id(parsed)
            if not full_content:
                full_content = parsed.text
        if not full_content and deferred_content:
            full_content = deferred_content

        final_tool_calls = parsed.tool_calls if parsed and parsed.tool_calls else tool_calls
        valid_tool_calls = [tc for tc in final_tool_calls if tc.name and tc.name.strip()]

        if valid_tool_calls:
            await self._execute_tool_calls_async(messages, valid_tool_calls, tools)
            return ToolLoopStreamResult(
                content="",
                has_tool_calls=True,
                usage=parsed.usage if parsed else {},
                response_id=parsed.response_id if parsed else None,
                completed_response=completed_response,
            )

        messages.append({"role": "assistant", "content": full_content})
        return ToolLoopStreamResult(
            content=full_content,
            has_tool_calls=False,
            usage={},
            response_id=self.last_response_id,
            completed_response=completed_response,
        )

    def _merge_chunks(self, chunks: List[str]) -> str:
        if not chunks:
            return ""
        if len(chunks) == 1:
            return chunks[0]

        result = chunks[0]
        for chunk in chunks[1:]:
            if chunk.startswith(result):
                result = chunk
            else:
                result += chunk
        return result

    def _accumulate_tool_calls(
        self, tool_calls: List[ToolCall], deltas: List[ToolCallDelta]
    ) -> None:
        for delta in deltas:
            if isinstance(delta, ToolCallDelta):
                delta.apply_to(tool_calls)

    def _execute_tool_calls_sync(
        self,
        messages: List[Any],
        tool_calls: List[ToolCall],
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        # Filter out tool calls with missing name
        valid_calls = [tc for tc in tool_calls if tc.name and tc.name.strip()]
        if not valid_calls:
            return
        self._ensure_tool_call_ids(valid_calls)

        messages.append({"role": "assistant", "tool_calls": [tc.as_chat_tool_call() for tc in valid_calls]})
        available_names = self._available_tool_names(available_tools)

        for tool_call in valid_calls:
            name = tool_call.name
            args = tool_call.arguments_dict()
            call_id = tool_call.id
            result = self._run_tool_sync(name, args, available_names)
            messages.append({"tool_call_id": call_id, "role": "tool", "name": name, "content": str(result)})

    async def _execute_tool_calls_async(
        self,
        messages: List[Any],
        tool_calls: List[ToolCall],
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        # Filter out tool calls with missing name or empty arguments
        valid_calls = [tc for tc in tool_calls if tc.name and tc.name.strip()]
        if not valid_calls:
            return
        self._ensure_tool_call_ids(valid_calls)

        messages.append({"role": "assistant", "tool_calls": [tc.as_chat_tool_call() for tc in valid_calls]})
        available_names = self._available_tool_names(available_tools)

        for tool_call in valid_calls:
            name = tool_call.name
            args = tool_call.arguments_dict()
            call_id = tool_call.id
            result = await self._run_tool_async(name, args, available_names)
            messages.append({"tool_call_id": call_id, "role": "tool", "name": name, "content": str(result)})

    def _available_tool_names(self, available_tools: Optional[List[Dict[str, Any]]]) -> Optional[set]:
        if not available_tools:
            return None
        return {t["function"]["name"] for t in available_tools if "function" in t}

    def _run_tool_sync(self, name: str, args: Dict[str, Any], available_names: Optional[set]) -> Any:
        if available_names and name not in available_names:
            return f"Unknown tool: {name}"
        if not name:
            return "Invalid tool call: missing tool name"
        try:
            return self.registry.execute_sync(name, **args)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _run_tool_async(self, name: str, args: Dict[str, Any], available_names: Optional[set]) -> Any:
        if available_names and name not in available_names:
            return f"Unknown tool: {name}"
        if not name:
            return "Invalid tool call: missing tool name"
        try:
            return await self.registry.execute(name, **args)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _ensure_tool_call_ids(self, tool_calls: List[ToolCall]) -> None:
        for tc in tool_calls:
            if not tc.id:
                tc.id = f"call_{uuid4().hex}"

    def _record_usage(self, parsed) -> None:
        if not self.metrics:
            return
        usage = parsed.usage or {}
        self.metrics.add_tokens(
            prompt_tokens=usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0,
        )

    def _update_last_response_id(self, parsed) -> None:
        self.last_response_id = parsed.response_id
