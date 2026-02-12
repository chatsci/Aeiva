from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from .function_catalog import (
    get_known_function_return_type,
    validate_known_function_call,
)
from .interaction_contract import (
    ACTION_VARIANTS,
    COMPONENT_SUPPORTED_EVENTS,
    FUNCTION_CALL_RETURN_TYPES,
)
from .protocol import UI_COMPONENT_TYPES

_INTERACTION_MODE_VALUES = frozenset({"interactive", "preview"})
_BUTTON_VARIANTS = frozenset({"primary", "borderless"})
_TEXTFIELD_VARIANTS = frozenset({"longText", "number", "shortText", "obscured"})
_CHOICE_PICKER_VARIANTS = frozenset({"multipleSelection", "mutuallyExclusive"})
_TEXT_VARIANTS = frozenset({"h1", "h2", "h3", "h4", "h5", "caption", "body"})
_IMAGE_FIT_VARIANTS = frozenset({"contain", "cover", "fill", "none", "scale-down"})
_IMAGE_VARIANT_VALUES = frozenset(
    {"icon", "avatar", "smallFeature", "mediumFeature", "largeFeature", "header"}
)
_DIVIDER_AXIS_VALUES = frozenset({"horizontal", "vertical"})
_INTERACTIVE_VALUE_BOUND_COMPONENTS = frozenset(
    {"TextField", "CheckBox", "ChoicePicker", "Slider", "DateTimeInput"}
)
_LAYOUT_ALIGN_VALUES = frozenset({"start", "center", "end", "stretch"})
_LAYOUT_JUSTIFY_VALUES = frozenset(
    {"center", "end", "spaceAround", "spaceBetween", "spaceEvenly", "start", "stretch"}
)
_LIST_DIRECTION_VALUES = frozenset({"vertical", "horizontal"})
_SHARED_OPTIONAL_PROP_KEYS = frozenset({"weight", "accessibility"})


def _to_finite_number(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _require_boolean_flag(value: Any, *, field_name: str) -> None:
    if isinstance(value, bool):
        return
    raise ValueError(f"{field_name} must be a boolean.")


def _normalize_interaction_mode(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "interactive"
    if text not in _INTERACTION_MODE_VALUES:
        raise ValueError(
            "interaction_mode must be 'interactive' or 'preview'. "
            f"Received: {value!r}"
        )
    return text


def _normalize_theme(theme: Any) -> Dict[str, Any]:
    if not isinstance(theme, Mapping):
        return {}
    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in theme.items():
        key = str(raw_key or "").strip()
        if not key or raw_value is None:
            continue
        if isinstance(raw_value, bool):
            normalized[key] = raw_value
            continue
        if isinstance(raw_value, (int, float)):
            number = _to_finite_number(raw_value)
            if number is None:
                continue
            normalized[key] = int(number) if int(number) == number else number
            continue
        normalized[key] = str(raw_value)
    return normalized


def _normalize_shared_component_props(
    component_type: str,
    props: Mapping[str, Any],
) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    if "weight" in normalized:
        weight = _to_finite_number(normalized.get("weight"))
        if weight is None:
            raise ValueError(f"{component_type}.props.weight must be a finite number.")
        normalized["weight"] = weight
    accessibility = normalized.get("accessibility")
    if accessibility is not None:
        if not isinstance(accessibility, Mapping):
            raise ValueError(f"{component_type}.props.accessibility must be an object.")
        normalized_accessibility = deepcopy(dict(accessibility))
        unknown = sorted(
            key for key in normalized_accessibility.keys() if str(key) not in {"label", "description"}
        )
        if unknown:
            raise ValueError(
                f"{component_type}.props.accessibility has unsupported keys: {unknown}. "
                "Allowed: ['description', 'label']."
            )
        normalized["accessibility"] = normalized_accessibility
    return normalized


def _validate_allowed_props(
    component_type: str,
    props: Mapping[str, Any],
    *,
    allowed: set[str],
) -> None:
    allowed_keys = set(allowed) | set(_SHARED_OPTIONAL_PROP_KEYS)
    unknown = sorted(key for key in props.keys() if str(key) not in allowed_keys)
    if unknown:
        raise ValueError(
            f"{component_type}.props has unsupported keys: {unknown}. "
            f"Allowed: {sorted(allowed_keys)}."
        )


def _coerce_component_ref(raw: Any, *, field_name: str) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"{field_name} must be a non-empty component id string.")
    token = raw.strip()
    if not token:
        raise ValueError(f"{field_name} must be a non-empty component id string.")
    return token


def _coerce_component_ref_list(raw: Any, *, field_name: str) -> list[str]:
    if not isinstance(raw, list):
        raise ValueError(f"{field_name} must be an array of component ids.")
    refs: list[str] = []
    for item in raw:
        refs.append(_coerce_component_ref(item, field_name=field_name))
    return refs


def _normalize_child_list(raw: Any, *, field_name: str) -> list[str] | Dict[str, Any]:
    if isinstance(raw, list):
        return _coerce_component_ref_list(raw, field_name=field_name)
    if isinstance(raw, Mapping):
        component_id = _coerce_component_ref(
            raw.get("componentId"), field_name=f"{field_name}.componentId"
        )
        path = str(raw.get("path") or "").strip()
        if not path:
            raise ValueError(f"{field_name}.path must be a non-empty JSON Pointer string.")
        out: Dict[str, Any] = {"componentId": component_id, "path": path}
        return out
    raise ValueError(
        f"{field_name} must be either an array of component ids or an object "
        "with {componentId, path}."
    )


def _normalize_dynamic_boolean_condition(raw_condition: Any, *, field_name: str) -> Any:
    if isinstance(raw_condition, bool):
        return raw_condition
    if not isinstance(raw_condition, Mapping):
        raise ValueError(
            f"{field_name} must be a boolean, data binding object, or function call object."
        )

    if "path" in raw_condition:
        path = str(raw_condition.get("path") or "").strip()
        if not path:
            raise ValueError(f"{field_name}.path must be a non-empty JSON Pointer.")
        unknown = sorted(key for key in raw_condition.keys() if str(key) != "path")
        if unknown:
            raise ValueError(
                f"{field_name} data binding has unsupported keys: {unknown}. Allowed: ['path']."
            )
        return {"path": path}

    call_name = str(raw_condition.get("call") or "").strip()
    if not call_name:
        raise ValueError(
            f"{field_name} must declare either a data binding {{path}} or a function call {{call,args}}."
        )
    expected_return_type = get_known_function_return_type(call_name)
    if expected_return_type is None:
        raise ValueError(
            f"{field_name}.call has unsupported function call '{call_name}'. "
            "Use a function name declared in the interaction contract function catalog."
        )
    if expected_return_type != "boolean":
        raise ValueError(
            f"{field_name}.call '{call_name}' must return 'boolean' in condition context."
        )

    normalized_condition: Dict[str, Any] = {"call": call_name}
    if "args" not in raw_condition:
        raise ValueError(f"{field_name}.args is required for function call conditions.")
    normalized_condition["args"] = validate_known_function_call(
        owner=field_name,
        call_name=call_name,
        args=raw_condition.get("args"),
    )

    return_type = raw_condition.get("returnType")
    if return_type is not None:
        token = str(return_type).strip()
        if token != "boolean":
            raise ValueError(f"{field_name}.returnType must be 'boolean'.")
        normalized_condition["returnType"] = token
    else:
        normalized_condition["returnType"] = "boolean"

    unknown = sorted(
        key for key in raw_condition.keys() if str(key) not in {"call", "args", "returnType"}
    )
    if unknown:
        raise ValueError(
            f"{field_name} function call has unsupported keys: {unknown}. "
            "Allowed: ['args', 'call', 'returnType']."
        )
    return normalized_condition


def _normalize_checks(raw_checks: Any) -> list[Dict[str, Any]]:
    if raw_checks is None:
        return []
    if not isinstance(raw_checks, list):
        raise ValueError("checks must be an array.")
    checks: list[Dict[str, Any]] = []
    for index, item in enumerate(raw_checks):
        if not isinstance(item, Mapping):
            raise ValueError(f"checks[{index}] must be an object.")
        unknown = sorted(key for key in item.keys() if str(key) not in {"condition", "message"})
        if unknown:
            raise ValueError(
                f"checks[{index}] has unsupported keys: {unknown}. "
                "Allowed: ['condition', 'message']."
            )
        if "condition" not in item:
            raise ValueError(f"checks[{index}].condition is required.")
        if "message" not in item:
            raise ValueError(f"checks[{index}].message is required.")
        normalized_check: Dict[str, Any] = {
            "condition": _normalize_dynamic_boolean_condition(
                item.get("condition"),
                field_name=f"checks[{index}].condition",
            ),
            "message": str(item.get("message")),
        }
        checks.append(normalized_check)
    return checks


def _set_normalized_checks(
    normalized_props: Dict[str, Any],
) -> None:
    checks = _normalize_checks(normalized_props.get("checks"))
    if checks:
        normalized_props["checks"] = checks
    else:
        normalized_props.pop("checks", None)


def _normalize_enum_field(
    normalized_props: Dict[str, Any],
    *,
    field_name: str,
    allowed_values: frozenset[str],
    error_label: str,
    default: Optional[str] = None,
) -> None:
    raw_value = normalized_props.get(field_name)
    if raw_value is None:
        if default is not None:
            normalized_props[field_name] = default
        return
    token = str(raw_value).strip()
    if token not in allowed_values:
        raise ValueError(f"{error_label} must be one of {sorted(allowed_values)}.")
    normalized_props[field_name] = token


def _normalize_action_object(raw_action: Any, *, owner: str) -> Dict[str, Any]:
    if not isinstance(raw_action, Mapping):
        raise ValueError(f"{owner}.action must be an object.")
    has_event = "event" in raw_action and raw_action.get("event") is not None
    has_function = "functionCall" in raw_action and raw_action.get("functionCall") is not None
    if has_event == has_function:
        raise ValueError(
            f"{owner}.action must include exactly one of {list(ACTION_VARIANTS)}."
        )

    if has_event:
        event = raw_action.get("event")
        if not isinstance(event, Mapping):
            raise ValueError(f"{owner}.action.event must be an object.")
        name = str(event.get("name") or "").strip()
        if not name:
            raise ValueError(f"{owner}.action.event.name is required.")
        context = event.get("context")
        normalized_event: Dict[str, Any] = {"name": name}
        if context is not None:
            if not isinstance(context, Mapping):
                raise ValueError(f"{owner}.action.event.context must be an object.")
            normalized_event["context"] = deepcopy(dict(context))
        unknown_event_keys = sorted(
            key for key in event.keys() if str(key) not in {"name", "context"}
        )
        if unknown_event_keys:
            raise ValueError(
                f"{owner}.action.event has unsupported keys: {unknown_event_keys}."
            )
        unknown_action_keys = sorted(
            key for key in raw_action.keys() if str(key) not in {"event"}
        )
        if unknown_action_keys:
            raise ValueError(
                f"{owner}.action has unsupported keys: {unknown_action_keys}."
            )
        return {"event": normalized_event}

    function_call = raw_action.get("functionCall")
    if not isinstance(function_call, Mapping):
        raise ValueError(f"{owner}.action.functionCall must be an object.")
    call_name = str(function_call.get("call") or "").strip()
    if not call_name:
        raise ValueError(f"{owner}.action.functionCall.call is required.")
    normalized_function: Dict[str, Any] = {"call": call_name}
    if "args" not in function_call:
        raise ValueError(f"{owner}.action.functionCall.args is required.")
    normalized_function["args"] = validate_known_function_call(
        owner=f"{owner}.action.functionCall",
        call_name=call_name,
        args=function_call.get("args"),
    )
    expected_return_type = get_known_function_return_type(call_name)
    if expected_return_type is None:
        raise ValueError(
            f"{owner}.action.functionCall.call has unsupported function call '{call_name}'."
        )
    return_type = function_call.get("returnType")
    if return_type is not None:
        token = str(return_type).strip()
        if token not in FUNCTION_CALL_RETURN_TYPES:
            raise ValueError(
                f"{owner}.action.functionCall.returnType must be one of "
                f"{list(FUNCTION_CALL_RETURN_TYPES)}."
            )
        if token != expected_return_type:
            raise ValueError(
                f"{owner}.action.functionCall.returnType for '{call_name}' must be "
                f"'{expected_return_type}'."
            )
        normalized_function["returnType"] = token
    else:
        normalized_function["returnType"] = expected_return_type
    unknown_function_keys = sorted(
        key for key in function_call.keys() if str(key) not in {"call", "args", "returnType"}
    )
    if unknown_function_keys:
        raise ValueError(
            f"{owner}.action.functionCall has unsupported keys: {unknown_function_keys}."
        )
    unknown_action_keys = sorted(
        key for key in raw_action.keys() if str(key) not in {"functionCall"}
    )
    if unknown_action_keys:
        raise ValueError(f"{owner}.action has unsupported keys: {unknown_action_keys}.")
    return {"functionCall": normalized_function}


def _extract_props(component: Mapping[str, Any]) -> Dict[str, Any]:
    raw_props = component.get("props")
    props: Dict[str, Any] = {}
    if raw_props is not None:
        if not isinstance(raw_props, Mapping):
            raise ValueError("component.props must be an object.")
        props = deepcopy(dict(raw_props))

    for raw_key, raw_value in component.items():
        key = str(raw_key or "")
        if key in {"id", "type", "component", "props"}:
            continue
        if key in props:
            raise ValueError(f"component field '{key}' is duplicated in props and top-level.")
        props[key] = deepcopy(raw_value)
    return props


def _expand_component_wrapper(component: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize component wrapper variants into canonical component mapping.

    Accepted canonical forms:
    - {"id": "...", "type": "Text", "props": {...}}
    - {"id": "...", "component": "Text", "props": {...}}

    Accepted wrapper form (A2UI docs/examples compatibility):
    - {"id": "...", "component": {"Text": {...}}}
    """

    normalized = deepcopy(dict(component))
    raw_component_value = normalized.get("component")
    if not isinstance(raw_component_value, Mapping):
        return normalized

    wrapper_items = list(raw_component_value.items())
    if len(wrapper_items) != 1:
        raise ValueError(
            "component wrapper object must contain exactly one component type key."
        )

    raw_type, raw_wrapper_props = wrapper_items[0]
    wrapper_type = str(raw_type or "").strip()
    if not wrapper_type:
        raise ValueError("component wrapper type key must be a non-empty string.")
    if raw_wrapper_props is None:
        wrapper_props: Dict[str, Any] = {}
    elif isinstance(raw_wrapper_props, Mapping):
        wrapper_props = deepcopy(dict(raw_wrapper_props))
    else:
        raise ValueError(
            "component wrapper value must be an object (component props)."
        )

    top_level_type = str(normalized.get("type") or "").strip()
    if top_level_type and top_level_type != wrapper_type:
        raise ValueError(
            f"component.type ('{top_level_type}') and wrapped component "
            f"type ('{wrapper_type}') must match."
        )

    top_level_props = normalized.get("props")
    merged_props: Dict[str, Any]
    if top_level_props is None:
        merged_props = {}
    elif isinstance(top_level_props, Mapping):
        merged_props = deepcopy(dict(top_level_props))
    else:
        raise ValueError("component.props must be an object.")

    for key, value in wrapper_props.items():
        key_text = str(key or "")
        if not key_text:
            continue
        if key_text in merged_props:
            raise ValueError(
                f"component wrapper prop '{key_text}' duplicates component.props."
            )
        merged_props[key_text] = deepcopy(value)

    normalized["component"] = wrapper_type
    normalized["type"] = wrapper_type
    normalized["props"] = merged_props
    return normalized


def _normalize_component_type(component: Mapping[str, Any]) -> str:
    type_value = component.get("type")
    component_value = component.get("component")
    type_text = str(type_value or "").strip()
    component_text = str(component_value or "").strip()
    if type_text and component_text and type_text != component_text:
        raise ValueError(
            f"component.type ('{type_text}') and component.component "
            f"('{component_text}') must match when both are provided."
        )
    resolved = type_text or component_text
    if not resolved:
        raise ValueError("component.type is required.")
    if resolved not in UI_COMPONENT_TYPES:
        raise ValueError(
            f"Unsupported component type: {resolved}. Allowed: {sorted(UI_COMPONENT_TYPES)}"
        )
    return resolved


def _normalize_layout_props(
    props: Mapping[str, Any],
    *,
    field_name: str,
) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props(
        field_name.removesuffix(".props"),
        props,
    )
    _validate_allowed_props(
        field_name.removesuffix(".props"),
        normalized,
        allowed={"children", "justify", "align"},
    )
    normalized["children"] = _normalize_child_list(
        normalized.get("children"),
        field_name=f"{field_name}.children",
    )
    _normalize_enum_field(
        normalized,
        field_name="justify",
        allowed_values=_LAYOUT_JUSTIFY_VALUES,
        error_label=f"{field_name}.justify",
    )
    _normalize_enum_field(
        normalized,
        field_name="align",
        allowed_values=_LAYOUT_ALIGN_VALUES,
        error_label=f"{field_name}.align",
    )
    weight = _to_finite_number(normalized.get("weight"))
    if weight is not None:
        normalized["weight"] = weight
    return normalized


def _normalize_list_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("List", props)
    _validate_allowed_props("List", normalized, allowed={"children", "direction", "align"})
    normalized["children"] = _normalize_child_list(
        normalized.get("children"),
        field_name="List.props.children",
    )
    _normalize_enum_field(
        normalized,
        field_name="direction",
        allowed_values=_LIST_DIRECTION_VALUES,
        error_label="List.props.direction",
    )
    _normalize_enum_field(
        normalized,
        field_name="align",
        allowed_values=_LAYOUT_ALIGN_VALUES,
        error_label="List.props.align",
    )
    return normalized


def _normalize_tabs_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Tabs", props)
    _validate_allowed_props("Tabs", normalized, allowed={"tabs"})
    tabs = normalized.get("tabs")
    if not isinstance(tabs, list) or not tabs:
        raise ValueError("Tabs.props.tabs must be a non-empty array.")
    parsed_tabs: list[Dict[str, Any]] = []
    for index, item in enumerate(tabs):
        if not isinstance(item, Mapping):
            raise ValueError(f"Tabs.props.tabs[{index}] must be an object.")
        title = item.get("title")
        if title is None:
            raise ValueError(f"Tabs.props.tabs[{index}].title is required.")
        child = _coerce_component_ref(
            item.get("child"),
            field_name=f"Tabs.props.tabs[{index}].child",
        )
        parsed_tabs.append(
            {
                "title": deepcopy(title),
                "child": child,
            }
        )
    normalized["tabs"] = parsed_tabs
    weight = _to_finite_number(normalized.get("weight"))
    if weight is not None:
        normalized["weight"] = weight
    return normalized


def _normalize_modal_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Modal", props)
    _validate_allowed_props("Modal", normalized, allowed={"trigger", "content"})
    normalized["trigger"] = _coerce_component_ref(
        normalized.get("trigger"), field_name="Modal.props.trigger"
    )
    normalized["content"] = _coerce_component_ref(
        normalized.get("content"), field_name="Modal.props.content"
    )
    return normalized


def _normalize_button_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Button", props)
    _validate_allowed_props(
        "Button",
        normalized,
        allowed={"child", "variant", "action", "checks"},
    )
    normalized["child"] = _coerce_component_ref(
        normalized.get("child"), field_name="Button.props.child"
    )
    _normalize_enum_field(
        normalized,
        field_name="variant",
        allowed_values=_BUTTON_VARIANTS,
        error_label="Button.props.variant",
        default="borderless",
    )
    action = normalized.get("action")
    if action is None:
        raise ValueError("Button.props.action is required.")
    normalized["action"] = _normalize_action_object(action, owner="Button.props")
    _set_normalized_checks(normalized)
    return normalized


def _normalize_textfield_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("TextField", props)
    _validate_allowed_props("TextField", normalized, allowed={"label", "value", "variant", "checks"})
    if normalized.get("label") is None:
        raise ValueError("TextField.props.label is required.")
    _normalize_enum_field(
        normalized,
        field_name="variant",
        allowed_values=_TEXTFIELD_VARIANTS,
        error_label="TextField.props.variant",
        default="shortText",
    )
    _set_normalized_checks(normalized)
    return normalized


def _normalize_checkbox_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("CheckBox", props)
    _validate_allowed_props("CheckBox", normalized, allowed={"label", "value", "checks"})
    if normalized.get("label") is None:
        raise ValueError("CheckBox.props.label is required.")
    if "value" not in normalized:
        raise ValueError("CheckBox.props.value is required.")
    _set_normalized_checks(normalized)
    return normalized


def _normalize_choice_picker_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("ChoicePicker", props)
    _validate_allowed_props(
        "ChoicePicker",
        normalized,
        allowed={"label", "variant", "options", "value", "checks"},
    )
    _normalize_enum_field(
        normalized,
        field_name="variant",
        allowed_values=_CHOICE_PICKER_VARIANTS,
        error_label="ChoicePicker.props.variant",
        default="mutuallyExclusive",
    )
    options = normalized.get("options")
    if not isinstance(options, list) or not options:
        raise ValueError("ChoicePicker.props.options must be a non-empty array.")
    parsed_options: list[Dict[str, Any]] = []
    for index, option in enumerate(options):
        if not isinstance(option, Mapping):
            raise ValueError(f"ChoicePicker.props.options[{index}] must be an object.")
        if "label" not in option or "value" not in option:
            raise ValueError(
                f"ChoicePicker.props.options[{index}] must include both label and value."
            )
        parsed_options.append(
            {
                "label": deepcopy(option.get("label")),
                "value": deepcopy(option.get("value")),
            }
        )
    normalized["options"] = parsed_options
    if "value" not in normalized:
        raise ValueError("ChoicePicker.props.value is required.")
    _set_normalized_checks(normalized)
    return normalized


def _normalize_slider_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Slider", props)
    _validate_allowed_props("Slider", normalized, allowed={"label", "value", "min", "max", "checks"})
    min_v = _to_finite_number(normalized.get("min"))
    max_v = _to_finite_number(normalized.get("max"))
    raw_value = normalized.get("value")
    value_v = _to_finite_number(raw_value)
    if min_v is None:
        raise ValueError("Slider.props.min is required and must be a finite number.")
    if max_v is None:
        raise ValueError("Slider.props.max is required and must be a finite number.")
    if max_v < min_v:
        min_v, max_v = max_v, min_v
    if raw_value is None:
        raise ValueError("Slider.props.value is required.")
    if value_v is not None:
        value_v = max(min_v, min(max_v, value_v))
        normalized["value"] = value_v
    elif not isinstance(raw_value, Mapping):
        raise ValueError("Slider.props.value must be a number or a dynamic binding object.")
    normalized["min"] = min_v
    normalized["max"] = max_v
    _set_normalized_checks(normalized)
    return normalized


def _normalize_datetime_input_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("DateTimeInput", props)
    _validate_allowed_props(
        "DateTimeInput",
        normalized,
        allowed={"value", "enableDate", "enableTime", "min", "max", "label", "checks"},
    )
    enable_date = normalized.get("enableDate", True)
    if not isinstance(enable_date, bool):
        raise ValueError("DateTimeInput.props.enableDate must be a boolean.")
    normalized["enableDate"] = enable_date
    enable_time = normalized.get("enableTime", False)
    if not isinstance(enable_time, bool):
        raise ValueError("DateTimeInput.props.enableTime must be a boolean.")
    normalized["enableTime"] = enable_time
    if "value" not in normalized:
        raise ValueError("DateTimeInput.props.value is required.")
    _set_normalized_checks(normalized)
    return normalized


def _normalize_text_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Text", props)
    _validate_allowed_props("Text", normalized, allowed={"text", "variant"})
    if "text" not in normalized:
        normalized["text"] = ""
    _normalize_enum_field(
        normalized,
        field_name="variant",
        allowed_values=_TEXT_VARIANTS,
        error_label="Text.props.variant",
    )
    return normalized


def _normalize_media_props(component_type: str, props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props(component_type, props)
    if component_type == "Image":
        allowed = {"url", "fit", "variant"}
    elif component_type == "Video":
        allowed = {"url"}
    else:
        allowed = {"url", "description"}
    _validate_allowed_props(component_type, normalized, allowed=allowed)
    if "url" not in normalized:
        raise ValueError(f"{component_type}.props.url is required.")
    if component_type == "Image":
        _normalize_enum_field(
            normalized,
            field_name="fit",
            allowed_values=_IMAGE_FIT_VARIANTS,
            error_label="Image.props.fit",
        )
        _normalize_enum_field(
            normalized,
            field_name="variant",
            allowed_values=_IMAGE_VARIANT_VALUES,
            error_label="Image.props.variant",
        )
    return normalized


def _normalize_image_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    return _normalize_media_props("Image", props)


def _normalize_video_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    return _normalize_media_props("Video", props)


def _normalize_audio_player_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    return _normalize_media_props("AudioPlayer", props)


def _normalize_icon_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Icon", props)
    _validate_allowed_props("Icon", normalized, allowed={"name"})
    if "name" not in normalized:
        normalized["name"] = ""
    return normalized


def _normalize_card_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Card", props)
    _validate_allowed_props("Card", normalized, allowed={"child"})
    normalized["child"] = _coerce_component_ref(
        normalized.get("child"), field_name="Card.props.child"
    )
    return normalized


def _normalize_divider_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_shared_component_props("Divider", props)
    _validate_allowed_props("Divider", normalized, allowed={"axis"})
    _normalize_enum_field(
        normalized,
        field_name="axis",
        allowed_values=_DIVIDER_AXIS_VALUES,
        error_label="Divider.props.axis",
    )
    return normalized


def _normalize_row_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    return _normalize_layout_props(props, field_name="Row.props")


def _normalize_column_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    return _normalize_layout_props(props, field_name="Column.props")


_COMPONENT_PROPS_NORMALIZERS: Dict[str, Callable[[Mapping[str, Any]], Dict[str, Any]]] = {
    "Text": _normalize_text_props,
    "Image": _normalize_image_props,
    "Video": _normalize_video_props,
    "AudioPlayer": _normalize_audio_player_props,
    "Icon": _normalize_icon_props,
    "Row": _normalize_row_props,
    "Column": _normalize_column_props,
    "List": _normalize_list_props,
    "Card": _normalize_card_props,
    "Tabs": _normalize_tabs_props,
    "Modal": _normalize_modal_props,
    "Divider": _normalize_divider_props,
    "Button": _normalize_button_props,
    "TextField": _normalize_textfield_props,
    "CheckBox": _normalize_checkbox_props,
    "ChoicePicker": _normalize_choice_picker_props,
    "Slider": _normalize_slider_props,
    "DateTimeInput": _normalize_datetime_input_props,
}


def _normalize_component_props(component_type: str, props: Mapping[str, Any]) -> Dict[str, Any]:
    normalizer = _COMPONENT_PROPS_NORMALIZERS.get(component_type)
    if normalizer is not None:
        return normalizer(props)
    return _normalize_shared_component_props(component_type, props)


def normalize_component(
    component: Mapping[str, Any],
    *,
    strict_component_types: bool = True,
) -> Dict[str, Any]:
    _require_boolean_flag(
        strict_component_types,
        field_name="strict_component_types",
    )
    if not isinstance(component, Mapping):
        raise ValueError("component must be an object.")
    normalized_component = _expand_component_wrapper(component)
    component_id = str(normalized_component.get("id") or "").strip()
    if not component_id:
        raise ValueError("component.id is required.")
    component_type = _normalize_component_type(normalized_component)
    props = _extract_props(normalized_component)
    normalized_props = _normalize_component_props(component_type, props)
    return {
        "id": component_id,
        "type": component_type,
        "props": normalized_props,
    }


def _collect_layout_refs(props: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    children = props.get("children")
    if isinstance(children, list):
        refs.extend(str(item) for item in children if str(item).strip())
    elif isinstance(children, Mapping):
        template_component_id = str(children.get("componentId") or "").strip()
        if template_component_id:
            refs.append(template_component_id)
    return refs


def _collect_card_refs(props: Mapping[str, Any]) -> list[str]:
    child = str(props.get("child") or "").strip()
    return [child] if child else []


def _collect_tabs_refs(props: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for item in props.get("tabs") or []:
        if not isinstance(item, Mapping):
            continue
        child = str(item.get("child") or "").strip()
        if child:
            refs.append(child)
    return refs


def _collect_modal_refs(props: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    trigger = str(props.get("trigger") or "").strip()
    content = str(props.get("content") or "").strip()
    if trigger:
        refs.append(trigger)
    if content:
        refs.append(content)
    return refs


_COMPONENT_REF_COLLECTORS: Dict[str, Callable[[Mapping[str, Any]], list[str]]] = {
    "Row": _collect_layout_refs,
    "Column": _collect_layout_refs,
    "List": _collect_layout_refs,
    "Card": _collect_card_refs,
    "Tabs": _collect_tabs_refs,
    "Modal": _collect_modal_refs,
    "Button": _collect_card_refs,
}


def _collect_component_refs(component: Mapping[str, Any]) -> list[str]:
    props = component.get("props")
    if not isinstance(props, Mapping):
        return []
    component_type = str(component.get("type") or "").strip()
    collector = _COMPONENT_REF_COLLECTORS.get(component_type)
    if collector is None:
        return []
    return collector(props)


def _has_dynamic_child_template(component: Mapping[str, Any]) -> bool:
    component_type = str(component.get("type") or "").strip()
    if component_type not in {"Row", "Column", "List"}:
        return False
    props = component.get("props")
    if not isinstance(props, Mapping):
        return False
    children = props.get("children")
    return isinstance(children, Mapping)


def _validate_component_graph(
    *,
    components: Sequence[Mapping[str, Any]],
    root_ids: Sequence[str],
) -> None:
    component_ids: set[str] = set()
    for component in components:
        component_id = str(component.get("id") or "").strip()
        if not component_id:
            continue
        if component_id in component_ids:
            raise ValueError(f"duplicate component id: {component_id}")
        component_ids.add(component_id)

    unknown_roots = [root_id for root_id in root_ids if root_id not in component_ids]
    if unknown_roots:
        raise ValueError(f"root contains unknown component ids: {unknown_roots}")

    adjacency: dict[str, list[str]] = {}
    has_dynamic_templates = False
    for component in components:
        component_id = str(component.get("id") or "").strip() or "<unknown>"
        if component_id != "<unknown>":
            adjacency[component_id] = []
        if _has_dynamic_child_template(component):
            has_dynamic_templates = True
        refs = _collect_component_refs(component)
        for ref in refs:
            if ref not in component_ids:
                raise ValueError(
                    f"component '{component_id}' references unknown child component '{ref}'."
                )
            if component_id != "<unknown>":
                adjacency.setdefault(component_id, []).append(ref)

    reachable: set[str] = set()
    frontier: list[str] = [root_id for root_id in root_ids if root_id in component_ids]
    while frontier:
        node = frontier.pop()
        if node in reachable:
            continue
        reachable.add(node)
        for child in adjacency.get(node, []):
            if child not in reachable:
                frontier.append(child)

    unreachable = sorted(component_ids - reachable)
    if unreachable and not has_dynamic_templates:
        raise ValueError(
            "spec contains unreachable components not connected from root: "
            f"{unreachable}"
        )


def _normalize_root(raw_root: Any) -> list[str]:
    if not isinstance(raw_root, list):
        raise ValueError("root must be a list of component ids.")
    root: list[str] = []
    for item in raw_root:
        token = _coerce_component_ref(item, field_name="root")
        if token not in root:
            root.append(token)
    if not root:
        raise ValueError("MetaUI spec must declare non-empty root component ids.")
    return root


def normalize_metaui_spec(
    spec: Mapping[str, Any],
    *,
    strict_component_types: bool = True,
) -> Dict[str, Any]:
    _require_boolean_flag(
        strict_component_types,
        field_name="strict_component_types",
    )
    if not isinstance(spec, Mapping):
        raise ValueError("MetaUI spec must be an object.")

    normalized = deepcopy(dict(spec))
    interaction_mode = _normalize_interaction_mode(
        normalized.get("interaction_mode")
    )
    normalized["interaction_mode"] = interaction_mode
    normalized["theme"] = _normalize_theme(normalized.get("theme"))
    normalized["title"] = str(normalized.get("title") or "MetaUI")
    raw_send_data_model = (
        normalized.get("send_data_model")
        if normalized.get("send_data_model") is not None
        else normalized.get("sendDataModel")
    )
    if raw_send_data_model is None:
        normalized["send_data_model"] = interaction_mode == "interactive"
    else:
        normalized["send_data_model"] = bool(raw_send_data_model)
    normalized.pop("sendDataModel", None)
    if not isinstance(normalized.get("state_bindings"), Mapping):
        normalized["state_bindings"] = {}
    else:
        normalized["state_bindings"] = deepcopy(dict(normalized["state_bindings"]))

    raw_actions = normalized.get("actions")
    if raw_actions is None:
        normalized.pop("actions", None)
    elif isinstance(raw_actions, list):
        if raw_actions:
            raise ValueError(
                "actions is not supported in strict A2UI mode. "
                "Use component-level Action (e.g., Button.props.action)."
            )
        normalized.pop("actions", None)
    else:
        raise ValueError("actions must be an array when provided.")

    raw_components = normalized.get("components")
    if not isinstance(raw_components, list):
        raise ValueError("components must be a list of component objects.")
    components = [normalize_component(item) for item in raw_components]
    if not components:
        raise ValueError(
            "MetaUI spec must include at least one renderable component. "
            "No fallback UI is injected by runtime."
        )
    root_ids = _normalize_root(normalized.get("root"))
    _validate_component_graph(components=components, root_ids=root_ids)

    normalized["components"] = components
    normalized["root"] = root_ids
    return normalized


def _normalize_partial_spec_fragment(fragment: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(fragment))
    if "interaction_mode" in normalized:
        normalized["interaction_mode"] = _normalize_interaction_mode(
            normalized.get("interaction_mode")
        )
    if "theme" in normalized:
        normalized["theme"] = _normalize_theme(normalized.get("theme"))
    if "send_data_model" in normalized or "sendDataModel" in normalized:
        raw_send_data_model = (
            normalized.get("send_data_model")
            if normalized.get("send_data_model") is not None
            else normalized.get("sendDataModel")
        )
        normalized["send_data_model"] = bool(raw_send_data_model)
        normalized.pop("sendDataModel", None)
    if "actions" in normalized:
        raw_actions = normalized.get("actions")
        if raw_actions is None:
            normalized.pop("actions", None)
        elif isinstance(raw_actions, list):
            if raw_actions:
                raise ValueError(
                    "patch.spec.actions is not supported in strict A2UI mode. "
                    "Use component-level Action (e.g., Button.props.action)."
                )
            normalized.pop("actions", None)
        else:
            raise ValueError("patch.spec.actions must be an array.")
    if "components" in normalized:
        raw_components = normalized.get("components")
        if not isinstance(raw_components, list):
            raise ValueError("patch.spec.components must be a list.")
        normalized["components"] = [normalize_component(item) for item in raw_components]
    if "root" in normalized:
        raw_root = normalized.get("root")
        if not isinstance(raw_root, list):
            raise ValueError("patch.spec.root must be a list of component ids.")
        root_ids: list[str] = []
        for item in raw_root:
            root_id = _coerce_component_ref(item, field_name="patch.spec.root")
            if root_id not in root_ids:
                root_ids.append(root_id)
        normalized["root"] = root_ids
    return normalized


def normalize_metaui_patch(
    patch: Mapping[str, Any],
    *,
    strict_component_types: bool = True,
) -> Dict[str, Any]:
    _require_boolean_flag(
        strict_component_types,
        field_name="strict_component_types",
    )
    if not isinstance(patch, Mapping):
        raise ValueError("patch must be an object.")
    normalized = deepcopy(dict(patch))
    op = str(normalized.get("op") or "").strip().lower()
    if op:
        normalized["op"] = op

    if op == "replace_spec":
        raw_spec = normalized.get("spec")
        if not isinstance(raw_spec, Mapping):
            raise ValueError("replace_spec patch requires object field `spec`.")
        normalized["spec"] = normalize_metaui_spec(raw_spec)
        return normalized

    if op == "merge_spec":
        raw_spec = normalized.get("spec")
        if not isinstance(raw_spec, Mapping):
            raise ValueError("merge_spec patch requires object field `spec`.")
        normalized["spec"] = _normalize_partial_spec_fragment(raw_spec)
        return normalized

    if op == "append_component":
        raw_component = normalized.get("component")
        if not isinstance(raw_component, Mapping):
            raise ValueError("append_component patch requires object field `component`.")
        normalized["component"] = normalize_component(raw_component)
        return normalized

    if op == "update_component":
        component_patch = normalized.get("component")
        if isinstance(component_patch, Mapping):
            normalized_component = normalize_component(component_patch)
            normalized["component"] = normalized_component
            normalized["id"] = str(
                normalized.get("id") or normalized_component.get("id") or ""
            ).strip()
            normalized["type"] = normalized_component.get("type")
            normalized["props"] = deepcopy(dict(normalized_component.get("props") or {}))
            if not normalized["id"]:
                raise ValueError("update_component patch requires target id.")
            return normalized

        target_id = str(normalized.get("id") or "").strip()
        if not target_id:
            raise ValueError("update_component patch requires `id`.")
        raw_type = normalized.get("type") or normalized.get("component")
        raw_props = normalized.get("props")
        if raw_type is not None:
            candidate = normalize_component(
                {
                    "id": target_id,
                    "type": raw_type,
                    "props": raw_props if isinstance(raw_props, Mapping) else {},
                }
            )
            normalized["type"] = candidate["type"]
            normalized["props"] = candidate["props"]
        elif raw_props is not None:
            if not isinstance(raw_props, Mapping):
                raise ValueError("update_component.props must be an object when provided.")
            normalized["props"] = deepcopy(dict(raw_props))
        return normalized

    if op == "set_root":
        normalized["root"] = _normalize_root(normalized.get("root"))
        return normalized

    if op == "set_title":
        normalized["title"] = str(normalized.get("title") or "")
        return normalized

    if isinstance(normalized.get("components"), list):
        return normalize_metaui_spec(normalized)
    return normalized


def collect_interaction_contract_issues(
    spec: Mapping[str, Any],
    *,
    require_explicit_interaction_contract: Optional[bool] = None,
) -> list[str]:
    _ = require_explicit_interaction_contract  # retained for API compatibility
    components = spec.get("components")
    if not isinstance(components, list):
        return ["`components` must be a list."]

    interaction_mode = _normalize_interaction_mode(spec.get("interaction_mode"))
    issues: list[str] = []
    if interaction_mode != "interactive":
        return issues

    interactive_component_types = set(COMPONENT_SUPPORTED_EVENTS.keys())
    actionable_components = 0

    def _has_path_value_binding(raw_value: Any) -> bool:
        if not isinstance(raw_value, Mapping):
            return False
        path = str(raw_value.get("path") or "").strip()
        return bool(path)

    for component in components:
        if not isinstance(component, Mapping):
            continue
        component_id = str(component.get("id") or "").strip() or "<unknown>"
        component_type = str(component.get("type") or "").strip()
        props = component.get("props")
        if not isinstance(props, Mapping):
            continue
        if component_type == "Button":
            action = props.get("action")
            if action is None:
                issues.append(
                    f"component '{component_id}' (Button) requires props.action in interactive mode."
                )
            else:
                try:
                    _normalize_action_object(action, owner=f"component '{component_id}'")
                    actionable_components += 1
                except Exception as exc:
                    issues.append(str(exc))
            continue

        if component_type in _INTERACTIVE_VALUE_BOUND_COMPONENTS:
            if not _has_path_value_binding(props.get("value")):
                issues.append(
                    f"component '{component_id}' ({component_type}) requires props.value "
                    "to be a data binding object with a non-empty `path` in interactive mode."
                )
            else:
                actionable_components += 1

        if component_type != "Button" and "action" in props:
            issues.append(
                f"component '{component_id}' ({component_type}) does not support props.action. "
                "Use Button.action to trigger server-side actions."
            )

    if actionable_components <= 0:
        issues.append(
            "interactive mode requires at least one actionable component: "
            "either a Button with props.action or an input component with props.value.path binding."
        )

    return issues
