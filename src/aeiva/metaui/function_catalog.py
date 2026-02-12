from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Final, Mapping


# Strict A2UI v0.10 standard function catalog.
# Source: specification/v0_10/json/standard_catalog.json
_STANDARD_FUNCTION_RETURN_TYPES: Final[Dict[str, str]] = {
    "required": "boolean",
    "regex": "boolean",
    "length": "boolean",
    "numeric": "boolean",
    "email": "boolean",
    "formatString": "string",
    "formatNumber": "string",
    "formatCurrency": "string",
    "formatDate": "string",
    "pluralize": "string",
    "openUrl": "void",
    "and": "boolean",
    "or": "boolean",
    "not": "boolean",
}

_STANDARD_FUNCTION_ARG_KEYS: Final[Dict[str, set[str]]] = {
    "required": {"value"},
    "regex": {"value", "pattern"},
    "length": {"value", "min", "max"},
    "numeric": {"value", "min", "max"},
    "email": {"value"},
    "formatString": {"value"},
    "formatNumber": {"value", "decimals", "grouping"},
    "formatCurrency": {"value", "currency", "decimals", "grouping"},
    "formatDate": {"value", "format"},
    "pluralize": {"value", "zero", "one", "two", "few", "many", "other"},
    "openUrl": {"url"},
    "and": {"values"},
    "or": {"values"},
    "not": {"value"},
}

# Backward-compatible export used by a2ui_runtime consistency checks.
STANDARD_FUNCTION_RETURN_TYPES: Final[Dict[str, str]] = _STANDARD_FUNCTION_RETURN_TYPES

# MetaUI local extension functions.
# These remain explicit, schema-validated function calls; no heuristic behavior.
_LOCAL_EXTENSION_FUNCTION_RETURN_TYPES: Final[Dict[str, str]] = {
    "setState": "void",
    "deleteState": "void",
    "appendState": "void",
    "prependState": "void",
    "mergeState": "void",
    "runSequence": "void",
}

_LOCAL_EXTENSION_FUNCTION_ARG_KEYS: Final[Dict[str, set[str]]] = {
    "setState": {"path", "value"},
    "deleteState": {"path"},
    "appendState": {"path", "value"},
    "prependState": {"path", "value"},
    "mergeState": {"path", "value"},
    "runSequence": {"steps"},
}

_SEQUENCE_ALLOWED_CALLS: Final[set[str]] = {
    "setState",
    "deleteState",
    "appendState",
    "prependState",
    "mergeState",
    "openUrl",
}

KNOWN_FUNCTION_RETURN_TYPES: Final[Dict[str, str]] = {
    **_STANDARD_FUNCTION_RETURN_TYPES,
    **_LOCAL_EXTENSION_FUNCTION_RETURN_TYPES,
}

_KNOWN_FUNCTION_ARG_KEYS: Final[Dict[str, set[str]]] = {
    **_STANDARD_FUNCTION_ARG_KEYS,
    **_LOCAL_EXTENSION_FUNCTION_ARG_KEYS,
}


def get_standard_function_catalog_snapshot() -> Dict[str, Any]:
    return {
        "return_types": deepcopy(_STANDARD_FUNCTION_RETURN_TYPES),
        "arg_keys": {name: sorted(keys) for name, keys in _STANDARD_FUNCTION_ARG_KEYS.items()},
    }


def get_function_catalog_snapshot() -> Dict[str, Any]:
    return {
        "return_types": deepcopy(KNOWN_FUNCTION_RETURN_TYPES),
        "arg_keys": {name: sorted(keys) for name, keys in _KNOWN_FUNCTION_ARG_KEYS.items()},
        "standard": sorted(_STANDARD_FUNCTION_RETURN_TYPES.keys()),
        "extensions": sorted(_LOCAL_EXTENSION_FUNCTION_RETURN_TYPES.keys()),
    }


def get_standard_function_return_type(call_name: str) -> str | None:
    """
    Legacy API: returns known function return type (standard + extensions).
    """
    return get_known_function_return_type(call_name)


def get_known_function_return_type(call_name: str) -> str | None:
    token = str(call_name or "").strip()
    if not token:
        return None
    return KNOWN_FUNCTION_RETURN_TYPES.get(token)


def validate_standard_function_call(
    *,
    owner: str,
    call_name: str,
    args: Any,
) -> Dict[str, Any]:
    """
    Legacy API: validates known function call (standard + extensions).
    """
    return validate_known_function_call(owner=owner, call_name=call_name, args=args)


def validate_known_function_call(
    *,
    owner: str,
    call_name: str,
    args: Any,
) -> Dict[str, Any]:
    token = str(call_name or "").strip()
    if not token:
        raise ValueError(f"{owner}.call is required.")

    expected_return_type = get_known_function_return_type(token)
    if expected_return_type is None:
        raise ValueError(
            f"{owner}.call has unsupported function call '{token}'. "
            f"Allowed: {sorted(KNOWN_FUNCTION_RETURN_TYPES.keys())}."
        )

    if not isinstance(args, Mapping):
        raise ValueError(f"{owner}.args must be an object.")
    normalized_args = deepcopy(dict(args))

    allowed_keys = _KNOWN_FUNCTION_ARG_KEYS[token]
    unknown = sorted(key for key in normalized_args.keys() if str(key) not in allowed_keys)
    if unknown:
        raise ValueError(
            f"{owner}.args has unsupported keys for '{token}': {unknown}. "
            f"Allowed: {sorted(allowed_keys)}."
        )

    if token in {"required", "regex", "length", "numeric", "email", "formatString", "formatNumber", "formatDate", "pluralize", "not"}:
        if "value" not in normalized_args:
            raise ValueError(f"{owner}.args.value is required for '{token}'.")
    if token == "regex" and "pattern" not in normalized_args:
        raise ValueError(f"{owner}.args.pattern is required for 'regex'.")
    if token in {"length", "numeric"} and ("min" not in normalized_args and "max" not in normalized_args):
        raise ValueError(f"{owner}.args must include at least one of ['min', 'max'] for '{token}'.")
    if token == "formatCurrency" and ("value" not in normalized_args or "currency" not in normalized_args):
        raise ValueError(f"{owner}.args must include ['value', 'currency'] for 'formatCurrency'.")
    if token == "formatDate" and "format" not in normalized_args:
        raise ValueError(f"{owner}.args.format is required for 'formatDate'.")
    if token == "openUrl" and "url" not in normalized_args:
        raise ValueError(f"{owner}.args.url is required for 'openUrl'.")
    if token in {"and", "or"}:
        values = normalized_args.get("values")
        if not isinstance(values, list) or len(values) < 2:
            raise ValueError(f"{owner}.args.values must be an array with at least 2 entries for '{token}'.")
    if token == "pluralize" and "other" not in normalized_args:
        raise ValueError(f"{owner}.args.other is required for 'pluralize'.")
    if token in {"setState", "appendState", "prependState", "mergeState"}:
        if "path" not in normalized_args:
            raise ValueError(f"{owner}.args.path is required for '{token}'.")
        if token != "deleteState" and "value" not in normalized_args:
            raise ValueError(f"{owner}.args.value is required for '{token}'.")
    if token == "deleteState" and "path" not in normalized_args:
        raise ValueError(f"{owner}.args.path is required for 'deleteState'.")
    if token == "runSequence":
        steps = normalized_args.get("steps")
        if not isinstance(steps, list) or len(steps) == 0:
            raise ValueError(f"{owner}.args.steps must be a non-empty array for 'runSequence'.")
        for index, raw_step in enumerate(steps):
            if not isinstance(raw_step, Mapping):
                raise ValueError(
                    f"{owner}.args.steps[{index}] must be an object with keys ['call', 'args']."
                )
            step_call = str(raw_step.get("call") or "").strip()
            if not step_call:
                raise ValueError(f"{owner}.args.steps[{index}].call is required.")
            if step_call not in _SEQUENCE_ALLOWED_CALLS:
                raise ValueError(
                    f"{owner}.args.steps[{index}].call '{step_call}' is not allowed for "
                    f"'runSequence'. Allowed: {sorted(_SEQUENCE_ALLOWED_CALLS)}."
                )
            step_args = raw_step.get("args", {})
            if not isinstance(step_args, Mapping):
                raise ValueError(f"{owner}.args.steps[{index}].args must be an object.")
            validate_known_function_call(
                owner=f"{owner}.args.steps[{index}]",
                call_name=step_call,
                args=step_args,
            )

    return normalized_args
