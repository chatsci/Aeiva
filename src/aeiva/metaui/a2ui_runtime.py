from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Iterable, List, Mapping, Sequence

from .function_catalog import STANDARD_FUNCTION_RETURN_TYPES

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_REGEX_PATTERN_LENGTH = 512
_MAX_REGEX_INPUT_LENGTH = 2048
_REGEX_NESTED_QUANTIFIER_RE = re.compile(r"\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*[+*]")
_REGEX_BACKREF_RE = re.compile(r"\\[1-9]")
_FORMAT_STRING_EXPR_RE = re.compile(r"(?<!\\)\$\{([^{}]+)\}")


def _is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(value)


def _decode_pointer_token(token: str) -> str:
    return str(token).replace("~1", "/").replace("~0", "~")


def _resolve_json_pointer(data_model: Any, path: str) -> Any:
    if path == "/" or not path:
        return data_model
    if not isinstance(data_model, Mapping):
        return None
    if not path.startswith("/"):
        return None
    cursor: Any = data_model
    for token in path[1:].split("/"):
        key = _decode_pointer_token(token)
        if isinstance(cursor, Mapping):
            if key not in cursor:
                return None
            cursor = cursor[key]
            continue
        if isinstance(cursor, Sequence) and not isinstance(cursor, (str, bytes, bytearray)):
            try:
                index = int(key)
            except Exception:
                return None
            if index < 0 or index >= len(cursor):
                return None
            cursor = cursor[index]
            continue
        return None
    return cursor


def _resolve_dotted_path(source: Any, path: str) -> Any:
    if not isinstance(source, Mapping):
        return None
    parts = [part for part in str(path).split(".") if part]
    cursor: Any = source
    for part in parts:
        if isinstance(cursor, Mapping):
            if part not in cursor:
                return None
            cursor = cursor[part]
            continue
        if isinstance(cursor, Sequence) and not isinstance(cursor, (str, bytes, bytearray)):
            try:
                idx = int(part)
            except Exception:
                return None
            if idx < 0 or idx >= len(cursor):
                return None
            cursor = cursor[idx]
            continue
        return None
    return cursor


def resolve_data_path(
    *,
    path: str,
    data_model: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> Any:
    text = str(path or "").strip()
    if not text:
        return None
    if text.startswith("/"):
        return _resolve_json_pointer(data_model, text)
    if context:
        from_context = _resolve_dotted_path(context, text)
        if from_context is not None:
            return from_context
    return _resolve_dotted_path(data_model, text)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _format_number(value: Any, *, digits: int | None = None, grouping: bool = True) -> str:
    try:
        number = float(value)
    except Exception:
        return str(value)
    if digits is None:
        text = f"{number:,.2f}" if grouping else f"{number:.2f}"
        return text.rstrip("0").rstrip(".")
    digits = max(0, min(int(digits), 12))
    return f"{number:,.{digits}f}" if grouping else f"{number:.{digits}f}"


def _function_required(args: Mapping[str, Any]) -> bool:
    return _is_truthy(args.get("value"))


def _function_email(args: Mapping[str, Any]) -> bool:
    value = str(args.get("value") or "").strip()
    return bool(_EMAIL_RE.match(value))


def _function_regex(args: Mapping[str, Any]) -> bool:
    value = str(args.get("value") or "")
    pattern = str(args.get("pattern") or "")
    if not pattern:
        return False
    if len(pattern) > _MAX_REGEX_PATTERN_LENGTH or len(value) > _MAX_REGEX_INPUT_LENGTH:
        return False
    if not _is_safe_regex_pattern(pattern):
        return False
    try:
        compiled = re.compile(pattern)
        return bool(compiled.search(value))
    except Exception:
        return False


def _is_safe_regex_pattern(pattern: str) -> bool:
    text = str(pattern or "")
    if not text:
        return False
    if _REGEX_BACKREF_RE.search(text):
        return False
    if _REGEX_NESTED_QUANTIFIER_RE.search(text):
        return False
    return True


def _function_numeric(args: Mapping[str, Any]) -> bool:
    try:
        value = float(args.get("value"))
    except Exception:
        return False
    min_v = args.get("min")
    max_v = args.get("max")
    if min_v is not None:
        try:
            if value < float(min_v):
                return False
        except Exception:
            return False
    if max_v is not None:
        try:
            if value > float(max_v):
                return False
        except Exception:
            return False
    return True


def _function_length(args: Mapping[str, Any]) -> bool:
    value = args.get("value")
    length = len(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else len(str(value or ""))
    min_v = args.get("min")
    max_v = args.get("max")
    if min_v is not None:
        try:
            if length < int(min_v):
                return False
        except Exception:
            return False
    if max_v is not None:
        try:
            if length > int(max_v):
                return False
        except Exception:
            return False
    return True


def _function_not(args: Mapping[str, Any]) -> bool:
    return not _is_truthy(args.get("value"))


def _function_and(args: Mapping[str, Any]) -> bool:
    values = args.get("values")
    if not isinstance(values, list) or len(values) < 2:
        return False
    return all(_is_truthy(item) for item in values)


def _function_or(args: Mapping[str, Any]) -> bool:
    values = args.get("values")
    if not isinstance(values, list) or len(values) < 2:
        return False
    return any(_is_truthy(item) for item in values)


def _function_format_number(args: Mapping[str, Any]) -> str:
    digits = args.get("decimals")
    grouping = True if args.get("grouping") is None else bool(args.get("grouping"))
    return _format_number(args.get("value"), digits=digits, grouping=grouping)


def _function_format_currency(args: Mapping[str, Any]) -> str:
    currency = str(args.get("currency") or "USD").upper()
    digits = args.get("decimals")
    grouping = True if args.get("grouping") is None else bool(args.get("grouping"))
    text = _format_number(
        args.get("value"),
        digits=digits if digits is not None else 2,
        grouping=grouping,
    )
    return f"{currency} {text}"


def _function_format_date(args: Mapping[str, Any]) -> str:
    dt = _parse_datetime(args.get("value"))
    if dt is None:
        return str(args.get("value") or "")
    fmt = str(args.get("format") or "").strip()
    if not fmt:
        return dt.isoformat()
    # Lightweight token mapping for common A2UI examples.
    fmt = (
        fmt.replace("YYYY", "%Y")
        .replace("MMM", "%b")
        .replace("MM", "%m")
        .replace("dd", "%d")
        .replace("d", "%d")
        .replace("hh", "%H")
        .replace("h", "%H")
        .replace("mm", "%M")
        .replace("ss", "%S")
        .replace("a", "%p")
        .replace("E", "%a")
    )
    try:
        return dt.strftime(fmt)
    except Exception:
        return dt.isoformat()


def _function_pluralize(args: Mapping[str, Any]) -> str:
    count = args.get("value")
    try:
        count_value = float(count)
    except Exception:
        count_value = 0.0

    if count_value == 0 and args.get("zero") is not None:
        return str(args.get("zero") or "")
    if count_value == 1 and args.get("one") is not None:
        return str(args.get("one") or "")
    if count_value == 2 and args.get("two") is not None:
        return str(args.get("two") or "")
    if count_value.is_integer() and abs(count_value) in {3, 4} and args.get("few") is not None:
        return str(args.get("few") or "")
    if count_value.is_integer() and abs(count_value) >= 5 and args.get("many") is not None:
        return str(args.get("many") or "")
    return str(args.get("other") or "")


def _function_open_url(args: Mapping[str, Any]) -> str:
    # Server-side evaluator returns normalized URL string and leaves side effect
    # to the client renderer/runtime.
    return str(args.get("url") or "")


def _function_format_string(
    args: Mapping[str, Any],
    *,
    data_model: Mapping[str, Any],
    context: Mapping[str, Any] | None,
) -> str:
    template = str(args.get("value") or "")
    if not template:
        return ""

    def _resolve_expr(match: re.Match[str]) -> str:
        token = str(match.group(1) or "").strip()
        if not token:
            return ""
        resolved = resolve_data_path(path=token, data_model=data_model, context=context)
        if resolved is None:
            return ""
        return str(resolved)

    rendered = _FORMAT_STRING_EXPR_RE.sub(_resolve_expr, template)
    return rendered.replace("\\${", "${")


_FUNCTION_TABLE = {
    "required": _function_required,
    "email": _function_email,
    "regex": _function_regex,
    "numeric": _function_numeric,
    "length": _function_length,
    "not": _function_not,
    "and": _function_and,
    "or": _function_or,
    "formatNumber": _function_format_number,
    "formatCurrency": _function_format_currency,
    "formatDate": _function_format_date,
    "formatString": _function_format_string,
    "pluralize": _function_pluralize,
    "openUrl": _function_open_url,
}

if set(_FUNCTION_TABLE.keys()) != set(STANDARD_FUNCTION_RETURN_TYPES.keys()):
    missing = sorted(set(STANDARD_FUNCTION_RETURN_TYPES.keys()) - set(_FUNCTION_TABLE.keys()))
    extra = sorted(set(_FUNCTION_TABLE.keys()) - set(STANDARD_FUNCTION_RETURN_TYPES.keys()))
    raise RuntimeError(
        "A2UI runtime function table drift detected. "
        f"Missing={missing}, Extra={extra}"
    )


def resolve_dynamic_value(
    value: Any,
    *,
    data_model: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> Any:
    if isinstance(value, Mapping):
        if "path" in value and isinstance(value.get("path"), str):
            resolved = resolve_data_path(path=value["path"], data_model=data_model, context=context)
            if resolved is None:
                return value.get("default")
            return resolved
        if "call" in value and isinstance(value.get("call"), str):
            args_raw = value.get("args")
            args = (
                resolve_dynamic_value(args_raw, data_model=data_model, context=context)
                if isinstance(args_raw, (Mapping, list))
                else args_raw
            )
            if not isinstance(args, Mapping):
                args = {}
            return evaluate_function_call(value["call"], args, data_model=data_model, context=context)
        return {
            str(key): resolve_dynamic_value(item, data_model=data_model, context=context)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [resolve_dynamic_value(item, data_model=data_model, context=context) for item in value]
    return value


def evaluate_function_call(
    call_name: str,
    args: Mapping[str, Any] | None,
    *,
    data_model: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> Any:
    name = str(call_name or "").strip()
    function = _FUNCTION_TABLE.get(name)
    if function is None:
        return None
    resolved_args = resolve_dynamic_value(args or {}, data_model=data_model or {}, context=context)
    if not isinstance(resolved_args, Mapping):
        resolved_args = {}
    try:
        return function(
            resolved_args,
            data_model=data_model or {},
            context=context,
        )
    except TypeError:
        return function(resolved_args)


def evaluate_check_definitions(
    *,
    checks: Iterable[Mapping[str, Any]],
    data_model: Mapping[str, Any],
    default_value: Any,
    context: Mapping[str, Any] | None = None,
) -> List[str]:
    errors: List[str] = []
    for check in checks:
        if not isinstance(check, Mapping):
            continue
        # Support both forms:
        # 1) legacy flat: {"call": "...", "args": {...}, "message": "..."}
        # 2) strict A2UI: {"condition": {"call": "...", "args": {...}}, "message": "..."}
        condition = check.get("condition")
        condition_mapping = condition if isinstance(condition, Mapping) else check

        call_name = str(condition_mapping.get("call") or "").strip()
        if not call_name:
            continue
        args = condition_mapping.get("args")
        resolved_args = resolve_dynamic_value(args or {}, data_model=data_model, context=context)
        if not isinstance(resolved_args, Mapping):
            resolved_args = {}
        if "value" not in resolved_args or resolved_args.get("value") is None:
            resolved_args = dict(resolved_args)
            resolved_args["value"] = default_value
        ok = bool(evaluate_function_call(call_name, resolved_args, data_model=data_model, context=context))
        if ok:
            continue
        message = str(check.get("message") or f"Validation failed: {call_name}")
        errors.append(message)
    return errors
