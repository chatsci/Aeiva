from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def _decode_pointer_token(token: str) -> str:
    return str(token).replace("~1", "/").replace("~0", "~")


def _encode_pointer_token(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _pointer_segments(path: str) -> List[str]:
    text = str(path or "").strip()
    if not text or text == "/":
        return []
    if not text.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {path}")
    return [_decode_pointer_token(part) for part in text[1:].split("/")]


def json_pointer_to_dotted_path(path: str) -> str:
    segments = _pointer_segments(path)
    if not segments:
        return ""
    return ".".join(segments)


def dotted_path_to_json_pointer(path: str) -> str:
    text = str(path or "").strip()
    if not text:
        return "/"
    tokens = [token.strip() for token in text.split(".") if token.strip()]
    if not tokens:
        return "/"
    return "/" + "/".join(_encode_pointer_token(token) for token in tokens)


def _encode_typed_value(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"valueNull": True}
    if isinstance(value, bool):
        return {"valueBoolean": value}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"valueNumber": float(value)}
    if isinstance(value, str):
        return {"valueString": value}
    if isinstance(value, Mapping):
        return {"valueMap": encode_object_to_contents(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return {"valueList": [_encode_typed_value(item) for item in value]}
    return {"valueString": str(value)}


def encode_object_to_contents(value: Mapping[str, Any]) -> List[Dict[str, Any]]:
    contents: List[Dict[str, Any]] = []
    for key, item in dict(value or {}).items():
        entry = {"key": str(key)}
        entry.update(_encode_typed_value(item))
        contents.append(entry)
    return contents


def _decode_typed_value(entry: Mapping[str, Any]) -> Any:
    block = dict(entry or {})
    if "valueMap" in block and isinstance(block["valueMap"], Iterable):
        return decode_contents_to_object(block["valueMap"])
    if "valueList" in block and isinstance(block["valueList"], Iterable):
        return [_decode_typed_value(item if isinstance(item, Mapping) else {}) for item in block["valueList"]]
    if "valueString" in block:
        return str(block["valueString"])
    if "valueNumber" in block:
        value = block["valueNumber"]
        try:
            return int(value) if float(value).is_integer() else float(value)
        except Exception:
            return float(value)
    if "valueBoolean" in block:
        return bool(block["valueBoolean"])
    if block.get("valueNull") is True:
        return None
    return None


def decode_contents_to_object(contents: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for item in contents or []:
        if not isinstance(item, Mapping):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        out[key] = _decode_typed_value(item)
    return out


def _merge_dict(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def merge_nested_dicts(
    base: Mapping[str, Any],
    incoming: Mapping[str, Any],
) -> Dict[str, Any]:
    return _merge_dict(dict(base or {}), dict(incoming or {}))


def apply_data_model_update(
    model: Mapping[str, Any],
    *,
    path: str,
    contents: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    next_model: Dict[str, Any] = deepcopy(dict(model or {}))
    payload = decode_contents_to_object(contents)
    segments = _pointer_segments(path)
    if not segments:
        return merge_nested_dicts(next_model, payload)

    cursor: Dict[str, Any] = next_model
    for segment in segments[:-1]:
        current = cursor.get(segment)
        if not isinstance(current, dict):
            current = {}
            cursor[segment] = current
        cursor = current

    leaf = segments[-1]
    existing = cursor.get(leaf)
    if isinstance(existing, dict):
        cursor[leaf] = merge_nested_dicts(existing, payload)
    else:
        cursor[leaf] = payload
    return next_model
