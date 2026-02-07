from dataclasses import dataclass
import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from uuid import uuid4

from aeiva.llm.backend import LLMBackend, LLMResponse
from aeiva.llm.llm_usage_metrics import LLMUsageMetrics
from aeiva.llm.tool_types import ToolCall, ToolCallDelta
from aeiva.tool.registry import get_registry

DEFAULT_TOOL_RESULT_MAX_CHARS = 8_000
_TOOL_RESULT_MAX_DEPTH = 4
_TOOL_RESULT_MAX_LIST_ITEMS = 80
_TOOL_RESULT_MAX_DICT_ITEMS = 120
_TOOL_RESULT_MAX_STRING_CHARS = 2_000


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
        tool_result_max_chars: int = DEFAULT_TOOL_RESULT_MAX_CHARS,
    ) -> None:
        self.backend = backend
        self.metrics = metrics
        self.max_tool_loops = max_tool_loops
        self.registry = registry or get_registry()
        self.last_response_id: Optional[str] = None
        self.tool_result_max_chars = self._normalize_tool_result_max_chars(tool_result_max_chars)

    def run(self, messages: List[Any], tools: List[Dict[str, Any]] = None, **kwargs) -> ToolLoopResult:
        for _ in range(self.max_tool_loops):
            self._sanitize_tool_history(messages)
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
            self._sanitize_tool_history(messages)
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
            self._sanitize_tool_history(messages)
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

    def _sanitize_tool_history(self, messages: List[Any]) -> None:
        """Ensure every assistant tool call has a matching tool result."""
        if not isinstance(messages, list):
            return

        tool_result_ids: set[str] = set()
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "tool":
                call_id = msg.get("tool_call_id")
                if call_id:
                    tool_result_ids.add(str(call_id))

        i = 0
        while i < len(messages):
            msg = messages[i]
            if not isinstance(msg, dict):
                i += 1
                continue

            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_calls = msg.get("tool_calls") or []
                missing: List[tuple[str, str]] = []
                for tc in tool_calls:
                    if isinstance(tc, ToolCall):
                        call_id = tc.id
                        name = tc.name
                    elif isinstance(tc, dict):
                        func = tc.get("function") or {}
                        call_id = tc.get("id") or tc.get("call_id") or ""
                        name = func.get("name") or tc.get("name") or ""
                    else:
                        call_id = getattr(tc, "id", None) or getattr(tc, "call_id", None) or ""
                        func = getattr(tc, "function", None)
                        name = (
                            getattr(func, "name", None)
                            if func is not None
                            else getattr(tc, "name", None)
                        ) or ""
                    if call_id and call_id not in tool_result_ids:
                        missing.append((str(call_id), name))

                if missing:
                    inserts = []
                    for call_id, name in missing:
                        inserts.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": name or "tool",
                            "content": self._format_tool_result({
                                "success": False,
                                "error": "tool_result_missing",
                                "message": "Missing tool result; previous tool call was cancelled or interrupted.",
                            }),
                        })
                        tool_result_ids.add(call_id)
                    messages[i + 1:i + 1] = inserts
                    i += len(inserts)

            i += 1

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
        start_len = len(messages)
        try:
            messages.append({"role": "assistant", "tool_calls": [tc.as_chat_tool_call() for tc in valid_calls]})
            available_names = self._available_tool_names(available_tools)

            for tool_call in valid_calls:
                name = tool_call.name
                args = tool_call.arguments_dict()
                call_id = tool_call.id
                result = self._run_tool_sync(name, args, available_names)
                messages.append({
                    "tool_call_id": call_id,
                    "role": "tool",
                    "name": name,
                    "content": self._format_tool_result(result),
                })
        except Exception:
            del messages[start_len:]
            raise

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

        start_len = len(messages)
        try:
            messages.append({"role": "assistant", "tool_calls": [tc.as_chat_tool_call() for tc in valid_calls]})
            available_names = self._available_tool_names(available_tools)

            for tool_call in valid_calls:
                name = tool_call.name
                args = tool_call.arguments_dict()
                call_id = tool_call.id
                result = await self._run_tool_async(name, args, available_names)
                messages.append({
                    "tool_call_id": call_id,
                    "role": "tool",
                    "name": name,
                    "content": self._format_tool_result(result),
                })
        except asyncio.CancelledError:
            # Roll back tool call messages to avoid dangling tool_calls without tool results.
            del messages[start_len:]
            raise
        except Exception:
            # Roll back partial tool-call messages on unexpected errors.
            del messages[start_len:]
            raise

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

    def _format_tool_result(self, result: Any) -> str:
        normalized = self._normalize_tool_result(result)
        if isinstance(normalized, str):
            return self._truncate_text(normalized, self.tool_result_max_chars)

        try:
            serialized = json.dumps(
                normalized,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError):
            return self._truncate_text(str(result), self.tool_result_max_chars)

        if len(serialized) <= self.tool_result_max_chars:
            return serialized

        preview = serialized[: max(0, self.tool_result_max_chars - 256)]
        while True:
            envelope = {
                "truncated": True,
                "original_length": len(serialized),
                "preview": preview,
            }
            try:
                truncated = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))
            except (TypeError, ValueError):
                return self._truncate_text(serialized, self.tool_result_max_chars)
            if len(truncated) <= self.tool_result_max_chars:
                return truncated
            if not preview:
                return self._truncate_text(truncated, self.tool_result_max_chars)
            overflow = len(truncated) - self.tool_result_max_chars
            trim = max(16, overflow + 8)
            preview = preview[:-trim]

    @staticmethod
    def _normalize_tool_result_max_chars(value: Any) -> int:
        try:
            parsed = int(value)
        except Exception:
            parsed = DEFAULT_TOOL_RESULT_MAX_CHARS
        return max(1_000, min(parsed, 60_000))

    @staticmethod
    def _truncate_text(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        if limit <= 64:
            return value[:limit]
        omitted = len(value) - limit
        suffix = f"...<truncated:{omitted} chars>"
        keep = max(1, limit - len(suffix))
        return value[:keep] + suffix

    def _normalize_tool_result(self, value: Any) -> Any:
        return self._normalize_tool_result_recursive(value, depth=0, seen=set())

    def _normalize_tool_result_recursive(
        self,
        value: Any,
        *,
        depth: int,
        seen: Set[int],
    ) -> Any:
        if depth > _TOOL_RESULT_MAX_DEPTH:
            return "<omitted:depth_limit>"

        if value is None or isinstance(value, (bool, int, float)):
            return value

        if isinstance(value, str):
            return self._truncate_text(value, _TOOL_RESULT_MAX_STRING_CHARS)

        if isinstance(value, (bytes, bytearray, memoryview)):
            return f"<binary:{len(value)} bytes>"

        if isinstance(value, dict):
            marker = id(value)
            if marker in seen:
                return "<omitted:cycle>"
            seen.add(marker)
            normalized: Dict[str, Any] = {}
            items = list(value.items())
            for idx, (raw_key, raw_val) in enumerate(items):
                if idx >= _TOOL_RESULT_MAX_DICT_ITEMS:
                    normalized["__truncated_fields__"] = len(items) - _TOOL_RESULT_MAX_DICT_ITEMS
                    break
                key = str(raw_key)
                normalized[key] = self._normalize_tool_result_recursive(
                    raw_val,
                    depth=depth + 1,
                    seen=seen,
                )
            seen.discard(marker)
            return normalized

        if isinstance(value, (list, tuple, set)):
            marker = id(value)
            if marker in seen:
                return ["<omitted:cycle>"]
            seen.add(marker)
            sequence = list(value)
            clipped = sequence[:_TOOL_RESULT_MAX_LIST_ITEMS]
            normalized_list = [
                self._normalize_tool_result_recursive(item, depth=depth + 1, seen=seen)
                for item in clipped
            ]
            if len(sequence) > _TOOL_RESULT_MAX_LIST_ITEMS:
                normalized_list.append(f"<truncated_items:{len(sequence) - _TOOL_RESULT_MAX_LIST_ITEMS}>")
            seen.discard(marker)
            return normalized_list

        return self._truncate_text(repr(value), _TOOL_RESULT_MAX_STRING_CHARS)

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
