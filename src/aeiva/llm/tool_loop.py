import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from aeiva.llm.adapters.base import LLMAdapter
from aeiva.llm.llm_usage_metrics import LLMUsageMetrics
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
        adapter: LLMAdapter,
        metrics: Optional[LLMUsageMetrics] = None,
        max_tool_loops: int = 10,
        registry=None,
    ) -> None:
        self.adapter = adapter
        self.metrics = metrics
        self.max_tool_loops = max_tool_loops
        self.registry = registry or get_registry()
        self.last_response_id: Optional[str] = None

    def run(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> ToolLoopResult:
        for _ in range(self.max_tool_loops):
            params = self.adapter.build_params(messages, tools, **kwargs)
            response = self.adapter.execute_sync(params)
            parsed = self.adapter.parse_response(response)

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
            params = self.adapter.build_params(messages, tools, **kwargs)
            response = await self.adapter.execute(params, stream=False)
            parsed = self.adapter.parse_response(response)

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
        params = self.adapter.build_params(messages, tools, **kwargs)
        response_stream = await self.adapter.execute(params, stream=True)

        tool_calls: List[Dict[str, Any]] = []
        chunks: List[str] = []
        completed_response = None

        async for chunk in response_stream:
            response_type = getattr(chunk, "type", None)
            if response_type and str(response_type).endswith("response.completed"):
                completed_response = getattr(chunk, "response", None)

            delta_content, delta_tool_calls = self.adapter.parse_stream_delta(
                chunk, response_type=response_type, has_accumulated=bool(chunks)
            )

            if delta_content:
                chunks.append(delta_content)
            if delta_tool_calls:
                self._accumulate_tool_calls(tool_calls, delta_tool_calls)

        full_content = self._merge_chunks(chunks)

        if tool_calls:
            await self._execute_tool_calls_async(messages, tool_calls, tools)
            return ToolLoopStreamResult(
                content="",
                has_tool_calls=True,
                usage={},
                response_id=None,
                completed_response=completed_response,
            )

        if not full_content and completed_response:
            parsed = self.adapter.parse_response(completed_response)
            full_content = parsed.text
            self._record_usage(parsed)
            self._update_last_response_id(parsed)
        elif completed_response:
            parsed = self.adapter.parse_response(completed_response)
            self._record_usage(parsed)
            self._update_last_response_id(parsed)

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
        self, tool_calls: List[Dict[str, Any]], deltas: List[Any]
    ) -> None:
        for chunk in deltas:
            index = getattr(chunk, "index", None) or len(tool_calls)
            while len(tool_calls) <= index:
                tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})

            tc = tool_calls[index]
            if chunk_id := getattr(chunk, "id", None):
                tc["id"] += chunk_id
            if func := getattr(chunk, "function", None):
                if name := getattr(func, "name", None):
                    tc["function"]["name"] += name
                if args := getattr(func, "arguments", None):
                    tc["function"]["arguments"] += args

    def _execute_tool_calls_sync(
        self,
        messages: List[Any],
        tool_calls: List[Any],
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        messages.append({"role": "assistant", "tool_calls": tool_calls})
        available_names = self._available_tool_names(available_tools)

        for tool_call in tool_calls:
            name, args, call_id = self._parse_tool_call(tool_call)
            result = self._run_tool_sync(name, args, available_names)
            messages.append({"tool_call_id": call_id, "role": "tool", "name": name, "content": str(result)})

    async def _execute_tool_calls_async(
        self,
        messages: List[Any],
        tool_calls: List[Any],
        available_tools: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        messages.append({"role": "assistant", "tool_calls": tool_calls})
        available_names = self._available_tool_names(available_tools)

        for tool_call in tool_calls:
            name, args, call_id = self._parse_tool_call(tool_call)
            result = await self._run_tool_async(name, args, available_names)
            messages.append({"tool_call_id": call_id, "role": "tool", "name": name, "content": str(result)})

    def _available_tool_names(self, available_tools: Optional[List[Dict[str, Any]]]) -> Optional[set]:
        if not available_tools:
            return None
        return {t["function"]["name"] for t in available_tools if "function" in t}

    def _parse_tool_call(self, tool_call: Any) -> Tuple[str, Dict[str, Any], str]:
        if isinstance(tool_call, dict):
            func = tool_call.get("function") or {}
            name = func.get("name", "")
            args_str = func.get("arguments", "{}")
            call_id = tool_call.get("id", "")
        else:
            func = getattr(tool_call, "function", None)
            name = getattr(func, "name", "") if func else ""
            args_str = getattr(func, "arguments", "{}") if func else "{}"
            call_id = getattr(tool_call, "id", "")

        try:
            args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
        except json.JSONDecodeError:
            args = {}

        return name, args, call_id

    def _run_tool_sync(self, name: str, args: Dict[str, Any], available_names: Optional[set]) -> Any:
        if available_names and name not in available_names:
            return f"Unknown tool: {name}"
        return self.registry.execute_sync(name, **args)

    async def _run_tool_async(self, name: str, args: Dict[str, Any], available_names: Optional[set]) -> Any:
        if available_names and name not in available_names:
            return f"Unknown tool: {name}"
        return await self.registry.execute(name, **args)

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
