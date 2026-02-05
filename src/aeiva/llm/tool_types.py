from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


def _stringify_arguments(arguments: Any) -> str:
    if arguments is None:
        return ""
    if isinstance(arguments, str):
        return arguments
    try:
        return json.dumps(arguments)
    except Exception:
        return str(arguments)


def _merge_fragment(existing: str, fragment: str) -> str:
    if not existing:
        return fragment
    if fragment.startswith(existing):
        return fragment
    return existing + fragment


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str

    @classmethod
    def from_any(cls, obj: Any) -> Optional["ToolCall"]:
        if obj is None:
            return None
        if isinstance(obj, ToolCall):
            return obj
        if isinstance(obj, dict):
            func = obj.get("function") or {}
            name = func.get("name") or obj.get("name")
            args = func.get("arguments") if "function" in obj else obj.get("arguments")
            call_id = obj.get("id") or obj.get("call_id") or ""
        else:
            func = getattr(obj, "function", None)
            if func is not None:
                name = getattr(func, "name", None)
                args = getattr(func, "arguments", None)
            else:
                name = getattr(obj, "name", None)
                args = getattr(obj, "arguments", None)
            call_id = getattr(obj, "id", None) or getattr(obj, "call_id", None) or ""

        if not name:
            return None

        return cls(id=str(call_id or ""), name=str(name), arguments=_stringify_arguments(args))

    def arguments_dict(self) -> Dict[str, Any]:
        if not self.arguments:
            return {}
        try:
            return json.loads(self.arguments) if isinstance(self.arguments, str) else (self.arguments or {})
        except json.JSONDecodeError:
            if isinstance(self.arguments, str):
                start = self.arguments.find("{")
                end = self.arguments.rfind("}")
                if start != -1 and end != -1 and end > start:
                    snippet = self.arguments[start:end + 1]
                    try:
                        parsed = json.loads(snippet)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        pass
            return {}

    def as_chat_tool_call(self) -> Dict[str, Any]:
        return {
            "id": self.id or "",
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments or "{}",
            },
        }


@dataclass
class ToolCallDelta:
    index: int
    id: Optional[str] = None
    name: Optional[str] = None
    arguments: Optional[str] = None

    @classmethod
    def from_any(cls, obj: Any, default_index: int = 0) -> Optional["ToolCallDelta"]:
        if obj is None:
            return None
        if isinstance(obj, ToolCallDelta):
            return obj
        if isinstance(obj, dict):
            index = obj.get("index", default_index)
            func = obj.get("function") or {}
            name = func.get("name") or obj.get("name")
            args = func.get("arguments") if "function" in obj else obj.get("arguments")
            call_id = obj.get("id") or obj.get("call_id")
        else:
            index = getattr(obj, "index", default_index)
            func = getattr(obj, "function", None)
            if func is not None:
                name = getattr(func, "name", None)
                args = getattr(func, "arguments", None)
            else:
                name = getattr(obj, "name", None)
                args = getattr(obj, "arguments", None)
            call_id = getattr(obj, "id", None)

        if call_id is None and name is None and args is None:
            return None

        return cls(
            index=int(index) if index is not None else default_index,
            id=str(call_id) if call_id else None,
            name=str(name) if name else None,
            arguments=_stringify_arguments(args) if args is not None else None,
        )

    def apply_to(self, calls: List[ToolCall]) -> None:
        while len(calls) <= self.index:
            calls.append(ToolCall(id="", name="", arguments=""))

        call = calls[self.index]
        if self.id:
            call.id = _merge_fragment(call.id, self.id)
        if self.name:
            call.name = _merge_fragment(call.name, self.name)
        if self.arguments:
            call.arguments = _merge_fragment(call.arguments, self.arguments)


def infer_tool_call_from_text(text: str, tools: Optional[Sequence[Dict[str, Any]]]) -> Optional[ToolCall]:
    if not text or not isinstance(text, str):
        return None
    stripped = text.strip()

    def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
        if raw.startswith("{") and raw.endswith("}"):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = raw[start:end + 1]
        try:
            parsed = json.loads(snippet)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    payload = _extract_json_object(stripped)
    if payload is None:
        return None

    if not isinstance(payload, dict):
        return None

    candidates: List[str] = []
    keys = set(payload.keys())

    for tool in tools or []:
        if not isinstance(tool, dict):
            continue
        if "function" in tool:
            func = tool.get("function") or {}
            name = func.get("name")
            params = func.get("parameters") or {}
        else:
            name = tool.get("name")
            params = tool.get("parameters") or {}

        if not name or not isinstance(params, dict):
            continue

        props = params.get("properties") or {}
        required = params.get("required") or []
        if not isinstance(props, dict):
            props = {}
        if not isinstance(required, list):
            required = []

        if required and not set(required).issubset(keys):
            continue
        if props and not keys.issubset(set(props.keys())):
            continue

        candidates.append(str(name))

    if len(candidates) != 1:
        return None

    return ToolCall(id="", name=candidates[0], arguments=json.dumps(payload))
