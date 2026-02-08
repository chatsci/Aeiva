from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from .protocol import UI_COMPONENT_TYPES

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")

_TYPE_ALIASES: Dict[str, str] = {
    "table": "data_table",
    "grid": "data_table",
    "data_grid": "data_table",
    "datagrid": "data_table",
    "tabset": "tabs",
    "tab_set": "tabs",
    "collapse": "accordion",
    "separator": "divider",
    "hr": "divider",
    "chat": "chat_panel",
    "chatbox": "chat_panel",
    "chat_box": "chat_panel",
    "chat_window": "chat_panel",
    "conversation": "chat_panel",
    "dialog": "chat_panel",
    "file_upload": "file_uploader",
    "upload": "file_uploader",
    "uploader": "file_uploader",
    "metric": "metric_card",
    "kpi": "metric_card",
    "stat": "metric_card",
    "list": "list_view",
    "listview": "list_view",
    "code": "code_block",
    "codeblock": "code_block",
    "pre": "code_block",
    "img": "image",
    "picture": "image",
    "embed": "iframe",
    "webview": "iframe",
    "btn": "button",
    "action_button": "button",
    "text_input": "input",
    "input_field": "input",
    "text_area": "textarea",
    "dropdown": "select",
    "toggle": "checkbox",
    "switch": "checkbox",
    "radio": "radio_group",
    "radiogroup": "radio_group",
    "range": "slider",
    "multi_step_form": "form_step",
    "step_form": "form_step",
    "form_wizard": "form_step",
    "wizard": "form_step",
    "progress": "progress_panel",
    "status_panel": "progress_panel",
    "export": "result_export",
    # A2UI standard component compatibility aliases.
    "row": "container",
    "column": "container",
    "card": "container",
    "modal": "container",
    "text_field": "input",
    "textfield": "input",
    "choice_picker": "select",
    "choicepicker": "select",
    "date_time_input": "input",
    "datetime_input": "input",
    "datetimeinput": "input",
    "icon": "badge",
    "video": "iframe",
    "audio_player": "iframe",
    "audioplayer": "iframe",
}

_LINE_CHART_ALIASES = {
    "line",
    "linechart",
    "line_chart",
    "plot",
    "timeseries",
    "time_series",
    "trend",
}
_BAR_CHART_ALIASES = {
    "bar",
    "barchart",
    "bar_chart",
    "column",
    "columns",
    "histogram",
}

_IFRAME_SANDBOX_PROFILES: Dict[str, str] = {
    "strict": "allow-same-origin",
    "interactive": "allow-same-origin allow-scripts allow-forms",
}
_IFRAME_ALLOWED_SANDBOX_TOKENS: set[str] = {
    "allow-downloads",
    "allow-forms",
    "allow-modals",
    "allow-popups",
    "allow-popups-to-escape-sandbox",
    "allow-presentation",
    "allow-same-origin",
    "allow-scripts",
}
_MAX_CHAT_MESSAGES = 200
_MAX_CHAT_MESSAGE_CHARS = 4000


def _norm_token(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return _TOKEN_SPLIT_RE.sub("_", text).strip("_")


def _component_type_token(component: Mapping[str, Any]) -> str:
    raw_type = component.get("type")
    if raw_type is None:
        raw_type = component.get("component")
    return _norm_token(raw_type)


def _component_raw_type(component: Mapping[str, Any]) -> Any:
    raw_type = component.get("type")
    if raw_type is None:
        raw_type = component.get("component")
    return raw_type


def _extract_component_props(component: Mapping[str, Any]) -> Dict[str, Any]:
    props_raw = component.get("props")
    props: Dict[str, Any] = deepcopy(dict(props_raw)) if isinstance(props_raw, Mapping) else {}
    for key, value in component.items():
        if key in {"id", "type", "component", "props"}:
            continue
        if key not in props:
            props[key] = deepcopy(value)
    return props


def _as_children_list(raw_children: Any, raw_child: Any) -> list[str]:
    if isinstance(raw_children, list):
        return [str(item) for item in raw_children if str(item).strip()]
    if raw_child is None:
        return []
    text = str(raw_child).strip()
    return [text] if text else []


def _normalize_checks(raw_checks: Any) -> list[Dict[str, Any]]:
    if not isinstance(raw_checks, list):
        return []
    checks: list[Dict[str, Any]] = []
    for item in raw_checks:
        if not isinstance(item, Mapping):
            continue
        call_name = str(item.get("call") or "").strip()
        if not call_name:
            continue
        check: Dict[str, Any] = {"call": call_name}
        args = item.get("args")
        if isinstance(args, Mapping):
            check["args"] = deepcopy(dict(args))
        message = item.get("message")
        if message is not None:
            check["message"] = str(message)
        checks.append(check)
    return checks


def _to_finite_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return number


def _coerce_chart_type(raw: Any) -> Optional[str]:
    token = _norm_token(raw)
    if token in _LINE_CHART_ALIASES:
        return "line"
    if token in _BAR_CHART_ALIASES:
        return "bar"
    return None


def _extract_points(data: Sequence[Any]) -> Tuple[list[str], list[float]]:
    labels: list[str] = []
    values: list[float] = []
    for index, item in enumerate(data):
        if isinstance(item, dict):
            raw_label = (
                item.get("label")
                or item.get("x")
                or item.get("name")
                or item.get("time")
                or item.get("date")
                or item.get("category")
            )
            raw_value = (
                item.get("value")
                if "value" in item
                else item.get("y")
                if "y" in item
                else item.get("count")
                if "count" in item
                else item.get("amount")
                if "amount" in item
                else item.get("score")
            )
            number = _to_finite_number(raw_value)
            if number is None:
                continue
            labels.append(str(raw_label if raw_label is not None else index + 1))
            values.append(number)
            continue

        number = _to_finite_number(item)
        if number is None:
            continue
        labels.append(str(index + 1))
        values.append(number)
    return labels, values


def _normalize_chart_props(props: Mapping[str, Any], *, inferred_chart_type: Optional[str]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))

    chart_type = _coerce_chart_type(
        normalized.get("chart_type") or normalized.get("kind") or normalized.get("mode")
    ) or inferred_chart_type or "bar"
    normalized["chart_type"] = chart_type

    labels = normalized.get("labels")
    values = normalized.get("values")

    valid_labels = isinstance(labels, list) and labels
    valid_values = isinstance(values, list) and values
    if not (valid_labels and valid_values):
        data = normalized.get("data")
        if isinstance(data, list) and data:
            labels, values = _extract_points(data)
        else:
            series = normalized.get("series")
            if isinstance(series, list) and series:
                primary = series[0]
                if isinstance(primary, dict):
                    if isinstance(primary.get("labels"), list) and isinstance(primary.get("values"), list):
                        labels = list(primary["labels"])
                        values = list(primary["values"])
                    elif isinstance(primary.get("data"), list):
                        labels, values = _extract_points(primary["data"])

    parsed_values: list[float] = []
    parsed_labels: list[str] = []
    if isinstance(values, list):
        candidate_labels = labels if isinstance(labels, list) else []
        for index, raw_value in enumerate(values):
            number = _to_finite_number(raw_value)
            if number is None:
                continue
            parsed_values.append(number)
            if index < len(candidate_labels):
                parsed_labels.append(str(candidate_labels[index]))
            else:
                parsed_labels.append(str(index + 1))

    if parsed_values:
        normalized["values"] = parsed_values
        normalized["labels"] = parsed_labels
    else:
        normalized.setdefault("values", [])
        normalized.setdefault("labels", [])

    return normalized


def _normalize_table_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    rows = normalized.get("rows")
    if rows is None and isinstance(normalized.get("data"), list):
        rows = normalized["data"]
    if not isinstance(rows, list):
        rows = []
    normalized["rows"] = rows

    columns = normalized.get("columns")
    if isinstance(columns, list) and columns:
        normalized["columns"] = [str(item) for item in columns]
        return normalized

    if rows and all(isinstance(item, dict) for item in rows):
        ordered: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                key_str = str(key)
                if key_str not in seen:
                    seen.add(key_str)
                    ordered.append(key_str)
        normalized["columns"] = ordered
    elif rows and all(isinstance(item, list) for item in rows):
        max_len = max(len(item) for item in rows)
        normalized["columns"] = [f"col_{index + 1}" for index in range(max_len)]
    else:
        normalized.setdefault("columns", [])
    return normalized


def _normalize_chat_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    messages = normalized.get("messages")
    if not isinstance(messages, list):
        messages = []

    parsed_messages: list[Dict[str, str]] = []
    content_trimmed_count = 0
    for item in messages:
        if isinstance(item, Mapping):
            role = str(item.get("role") or item.get("speaker") or "assistant").strip().lower()
            content = item.get("content")
            if content is None:
                content = item.get("text")
            if content is None:
                continue
            text = str(content)
            if len(text) > _MAX_CHAT_MESSAGE_CHARS:
                text = text[:_MAX_CHAT_MESSAGE_CHARS]
                content_trimmed_count += 1
            parsed_messages.append(
                {
                    "role": "user" if role in {"user", "human", "client"} else "assistant",
                    "content": text,
                }
            )
            continue
        if isinstance(item, str) and item.strip():
            text = item.strip()
            if len(text) > _MAX_CHAT_MESSAGE_CHARS:
                text = text[:_MAX_CHAT_MESSAGE_CHARS]
                content_trimmed_count += 1
            parsed_messages.append({"role": "assistant", "content": text})

    dropped_count = 0
    if len(parsed_messages) > _MAX_CHAT_MESSAGES:
        dropped_count = len(parsed_messages) - _MAX_CHAT_MESSAGES
        parsed_messages = parsed_messages[-_MAX_CHAT_MESSAGES:]
    normalized["messages"] = parsed_messages
    if dropped_count > 0:
        normalized["messages_truncated"] = True
        normalized["messages_truncated_count"] = dropped_count
    if content_trimmed_count > 0:
        normalized["message_content_truncated"] = True
        normalized["message_content_truncated_count"] = content_trimmed_count
    if "placeholder" in normalized and normalized["placeholder"] is not None:
        normalized["placeholder"] = str(normalized["placeholder"])
    if "send_label" in normalized and normalized["send_label"] is not None:
        normalized["send_label"] = str(normalized["send_label"])
    if "empty_text" in normalized and normalized["empty_text"] is not None:
        normalized["empty_text"] = str(normalized["empty_text"])
    return normalized


def _normalize_button_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    label = normalized.get("label") or normalized.get("text") or normalized.get("title") or "Action"
    normalized["label"] = str(label)
    event_type = normalized.get("event_type") or "action"
    normalized["event_type"] = str(event_type)
    payload = normalized.get("payload")
    normalized["payload"] = deepcopy(payload) if isinstance(payload, Mapping) else {}
    variant = str(normalized.get("variant") or "secondary").strip().lower()
    normalized["variant"] = variant if variant in {"primary", "secondary"} else "secondary"
    return normalized


def _normalize_input_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    normalized["name"] = str(normalized.get("name") or "input")
    normalized["label"] = str(normalized.get("label") or normalized["name"])
    input_type = _norm_token(normalized.get("input_type") or normalized.get("type") or "text")
    if input_type not in {"text", "number", "date", "time", "email", "url", "password", "search"}:
        input_type = "text"
    normalized["input_type"] = input_type
    if "placeholder" in normalized and normalized["placeholder"] is not None:
        normalized["placeholder"] = str(normalized["placeholder"])
    value_raw = normalized.get("value")
    if isinstance(value_raw, Mapping):
        normalized["value"] = deepcopy(dict(value_raw))
    elif input_type == "number":
        number = _to_finite_number(value_raw)
        normalized["value"] = number if number is not None else 0
    elif value_raw is not None:
        normalized["value"] = str(value_raw)
    else:
        normalized["value"] = ""
    checks = _normalize_checks(normalized.get("checks"))
    if checks:
        normalized["checks"] = checks
    return normalized


def _normalize_textarea_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    normalized["name"] = str(normalized.get("name") or "textarea")
    normalized["label"] = str(normalized.get("label") or normalized["name"])
    value_raw = normalized.get("value")
    if isinstance(value_raw, Mapping):
        normalized["value"] = deepcopy(dict(value_raw))
    else:
        normalized["value"] = str(value_raw or "")
    rows = normalized.get("rows")
    try:
        rows_int = int(rows)
    except Exception:
        rows_int = 4
    normalized["rows"] = min(max(rows_int, 2), 20)
    checks = _normalize_checks(normalized.get("checks"))
    if checks:
        normalized["checks"] = checks
    return normalized


def _normalize_option_list(raw_options: Any) -> list[Dict[str, str]]:
    if not isinstance(raw_options, list):
        return []
    parsed: list[Dict[str, str]] = []
    for item in raw_options:
        if isinstance(item, Mapping):
            value = str(item.get("value") if item.get("value") is not None else item.get("label") or "")
            label = str(item.get("label") if item.get("label") is not None else value)
            if not value and not label:
                continue
            parsed.append({"label": label or value, "value": value or label})
            continue
        if item is None:
            continue
        text = str(item)
        if not text:
            continue
        parsed.append({"label": text, "value": text})
    return parsed


def _normalize_select_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    normalized["name"] = str(normalized.get("name") or "select")
    normalized["label"] = str(normalized.get("label") or normalized["name"])
    options = _normalize_option_list(normalized.get("options"))
    normalized["options"] = options
    value = normalized.get("value")
    if value is None and options:
        value = options[0]["value"]
    if isinstance(value, Mapping):
        normalized["value"] = deepcopy(dict(value))
    else:
        normalized["value"] = str(value) if value is not None else ""
    checks = _normalize_checks(normalized.get("checks"))
    if checks:
        normalized["checks"] = checks
    return normalized


def _normalize_checkbox_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    normalized["name"] = str(normalized.get("name") or "checkbox")
    normalized["label"] = str(normalized.get("label") or normalized["name"])
    value = normalized.get("checked")
    if value is None:
        value = normalized.get("value")
    if value is None:
        value = normalized.get("default")
    normalized["checked"] = bool(value)
    return normalized


def _normalize_radio_group_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    normalized["name"] = str(normalized.get("name") or "radio_group")
    normalized["label"] = str(normalized.get("label") or normalized["name"])
    options = _normalize_option_list(normalized.get("options"))
    normalized["options"] = options
    value = normalized.get("value")
    if value is None and options:
        value = options[0]["value"]
    if isinstance(value, Mapping):
        normalized["value"] = deepcopy(dict(value))
    else:
        normalized["value"] = str(value) if value is not None else ""
    checks = _normalize_checks(normalized.get("checks"))
    if checks:
        normalized["checks"] = checks
    return normalized


def _normalize_slider_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    normalized["name"] = str(normalized.get("name") or "slider")
    normalized["label"] = str(normalized.get("label") or normalized["name"])
    min_v = _to_finite_number(normalized.get("min"))
    max_v = _to_finite_number(normalized.get("max"))
    step_v = _to_finite_number(normalized.get("step"))
    value_v = _to_finite_number(normalized.get("value"))
    min_v = 0.0 if min_v is None else min_v
    max_v = 100.0 if max_v is None else max_v
    if max_v < min_v:
        min_v, max_v = max_v, min_v
    step_v = 1.0 if step_v is None or step_v <= 0 else step_v
    if value_v is None:
        value_v = min_v
    value_v = max(min_v, min(max_v, value_v))
    normalized["min"] = min_v
    normalized["max"] = max_v
    normalized["step"] = step_v
    normalized["value"] = value_v
    return normalized


def _normalize_metric_card_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    normalized["label"] = str(normalized.get("label") or normalized.get("title") or "Metric")
    value = normalized.get("value")
    normalized["value"] = value if value is not None else "--"
    if normalized.get("delta") is not None:
        normalized["delta"] = normalized.get("delta")
    if normalized.get("description") is not None:
        normalized["description"] = str(normalized.get("description"))
    tone = str(normalized.get("tone") or "neutral").strip().lower()
    normalized["tone"] = tone
    return normalized


def _normalize_list_view_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    items = normalized.get("items")
    if not isinstance(items, list):
        items = normalized.get("rows") if isinstance(normalized.get("rows"), list) else []
    normalized["items"] = deepcopy(items)
    if normalized.get("title") is not None:
        normalized["title"] = str(normalized.get("title"))
    return normalized


def _normalize_tabs_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    raw_tabs = normalized.get("tabs")
    tabs: list[Dict[str, Any]] = []
    if isinstance(raw_tabs, list):
        for index, item in enumerate(raw_tabs):
            if not isinstance(item, Mapping):
                continue
            tab_id = str(item.get("id") or f"tab_{index + 1}").strip()
            label = str(item.get("label") or tab_id or f"Tab {index + 1}")
            children = item.get("children")
            children = [str(child) for child in children] if isinstance(children, list) else []
            tabs.append({"id": tab_id, "label": label, "children": children})
    normalized["tabs"] = tabs
    active = normalized.get("active_tab")
    if active is None and tabs:
        active = tabs[0]["id"]
    normalized["active_tab"] = str(active) if active is not None else ""
    return normalized


def _normalize_accordion_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    raw_sections = normalized.get("sections")
    sections: list[Dict[str, Any]] = []
    if isinstance(raw_sections, list):
        for index, item in enumerate(raw_sections):
            if not isinstance(item, Mapping):
                continue
            section_id = str(item.get("id") or f"section_{index + 1}").strip()
            title = str(item.get("title") or section_id or f"Section {index + 1}")
            children = item.get("children")
            children = [str(child) for child in children] if isinstance(children, list) else []
            sections.append({"id": section_id, "title": title, "children": children})
    normalized["sections"] = sections
    open_section = normalized.get("open_section")
    if open_section is None and sections:
        open_section = sections[0]["id"]
    normalized["open_section"] = str(open_section) if open_section is not None else ""
    return normalized


def _normalize_image_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    src = normalized.get("src")
    if src is None:
        src = normalized.get("url")
    normalized["src"] = str(src or "")
    normalized["alt"] = str(normalized.get("alt") or "")
    width = _to_finite_number(normalized.get("width"))
    height = _to_finite_number(normalized.get("height"))
    if width is not None:
        normalized["width"] = int(width)
    if height is not None:
        normalized["height"] = int(height)
    fit = str(normalized.get("fit") or "contain").strip().lower()
    normalized["fit"] = fit if fit in {"contain", "cover", "fill", "none", "scale-down"} else "contain"
    return normalized


def _normalize_iframe_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    src = normalized.get("src")
    if src is None:
        src = normalized.get("url")
    normalized["src"] = str(src or "")
    height = _to_finite_number(normalized.get("height"))
    normalized["height"] = int(height) if height is not None else 420
    profile = _norm_token(normalized.get("sandbox_profile")) or "strict"
    if profile not in _IFRAME_SANDBOX_PROFILES:
        profile = "strict"
    sandbox = normalized.get("sandbox")
    if sandbox is None:
        normalized["sandbox"] = _IFRAME_SANDBOX_PROFILES[profile]
    else:
        normalized["sandbox"] = _normalize_iframe_sandbox(str(sandbox), default_profile=profile)
    normalized["sandbox_profile"] = profile
    return normalized


def _normalize_iframe_sandbox(sandbox: str, *, default_profile: str) -> str:
    tokens = [item.strip().lower() for item in str(sandbox or "").split() if item and item.strip()]
    filtered = [item for item in tokens if item in _IFRAME_ALLOWED_SANDBOX_TOKENS]
    if not filtered:
        return _IFRAME_SANDBOX_PROFILES.get(default_profile, _IFRAME_SANDBOX_PROFILES["strict"])
    ordered = sorted(set(filtered))
    return " ".join(ordered)


def _normalize_code_block_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    code = normalized.get("code")
    if code is None:
        code = normalized.get("text")
    normalized["code"] = str(code or "")
    if normalized.get("language") is not None:
        normalized["language"] = str(normalized.get("language"))
    if normalized.get("title") is not None:
        normalized["title"] = str(normalized.get("title"))
    return normalized


def _normalize_divider_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    if normalized.get("label") is not None:
        normalized["label"] = str(normalized.get("label"))
    return normalized


def _normalize_container_props(props: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(dict(props))
    direction = _norm_token(normalized.get("direction") or "column")
    normalized["direction"] = "row" if direction == "row" else "column"
    children = normalized.get("children")
    if isinstance(children, list):
        normalized["children"] = [str(item) for item in children if str(item).strip()]
    else:
        normalized["children"] = []
    if normalized.get("title") is not None:
        normalized["title"] = str(normalized.get("title"))
    if normalized.get("justify") is not None:
        normalized["justify"] = str(normalized.get("justify"))
    if normalized.get("align") is not None:
        normalized["align"] = str(normalized.get("align"))
    if normalized.get("card") is not None:
        normalized["card"] = bool(normalized["card"])
    if normalized.get("modal") is not None:
        normalized["modal"] = bool(normalized["modal"])
    return normalized


def _normalize_theme(theme: Any) -> Dict[str, Any]:
    if not isinstance(theme, Mapping):
        return {}
    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in theme.items():
        key = _norm_token(raw_key)
        if not key:
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
        if raw_value is None:
            continue
        normalized[key] = str(raw_value)
    return normalized


def _normalize_component_type(raw_type: Any) -> tuple[str, Optional[str]]:
    token = _norm_token(raw_type)
    aliased = _TYPE_ALIASES.get(token)
    if aliased and aliased != "chart":
        return aliased, None
    inferred_chart_type = _coerce_chart_type(token)
    if inferred_chart_type is not None:
        return "chart", inferred_chart_type
    if token in UI_COMPONENT_TYPES:
        return token, None
    return _TYPE_ALIASES.get(token, str(raw_type or "")), None


def normalize_component(
    component: Mapping[str, Any],
    *,
    strict_component_types: bool = False,
) -> Dict[str, Any]:
    normalized = deepcopy(dict(component))
    raw_type = _component_raw_type(normalized)
    type_token = _component_type_token(normalized)
    component_type, inferred_chart_type = _normalize_component_type(raw_type)
    props = _extract_component_props(normalized)

    if type_token == "row":
        props.setdefault("direction", "row")
        props["children"] = _as_children_list(props.get("children"), props.get("child"))
    elif type_token == "column":
        props.setdefault("direction", "column")
        props["children"] = _as_children_list(props.get("children"), props.get("child"))
    elif type_token == "card":
        props.setdefault("direction", "column")
        props["card"] = True
        props["children"] = _as_children_list(props.get("children"), props.get("child"))
    elif type_token == "modal":
        props.setdefault("direction", "column")
        props["modal"] = True
        props["card"] = True
        props["children"] = _as_children_list(props.get("children"), props.get("child"))
    elif type_token in {"textfield", "text_field"}:
        variant = _norm_token(props.get("variant"))
        if variant in {"long_text", "longtext", "paragraph"}:
            component_type = "textarea"
        else:
            component_type = "input"
            props.setdefault("input_type", "text")
        props.setdefault("name", str(normalized.get("id") or "field"))
    elif type_token in {"choicepicker", "choice_picker"}:
        variant = _norm_token(props.get("variant"))
        component_type = "radio_group" if variant in {"mutuallyexclusive", "mutually_exclusive"} else "select"
        props.setdefault("name", str(normalized.get("id") or "choice"))
    elif type_token in {"datetimeinput", "date_time_input", "datetime_input"}:
        component_type = "input"
        variant = _norm_token(props.get("variant"))
        mode = _norm_token(props.get("mode"))
        resolved = variant or mode
        if resolved in {"datetime", "date_time", "dateandtime"}:
            props["input_type"] = "datetime-local"
        elif resolved == "time":
            props["input_type"] = "time"
        else:
            props["input_type"] = "date"
        props.setdefault("name", str(normalized.get("id") or "datetime"))
    elif type_token == "icon":
        component_type = "badge"
        icon_name = props.get("name")
        if isinstance(icon_name, Mapping):
            icon_name = icon_name.get("path")
        props["text"] = str(icon_name or props.get("text") or props.get("label") or "icon")
    elif type_token == "video":
        component_type = "iframe"
        props["src"] = props.get("url") or props.get("src") or ""
        props.setdefault("height", 360)
    elif type_token in {"audioplayer", "audio_player"}:
        component_type = "iframe"
        props["src"] = props.get("url") or props.get("src") or ""
        props.setdefault("height", 120)
        if props.get("description") is not None and props.get("title") is None:
            props["title"] = props.get("description")

    if component_type not in UI_COMPONENT_TYPES:
        if strict_component_types:
            raise ValueError(
                f"Unsupported component type: {component_type}. Allowed: {sorted(UI_COMPONENT_TYPES)}"
            )
        text = (
            props.get("text")
            or props.get("label")
            or props.get("title")
            or f"Unsupported component '{component_type}' normalized to text."
        )
        normalized["type"] = "text"
        normalized["props"] = {
            "text": str(text),
            "card": bool(props.get("card", True)),
        }
        return normalized

    normalized["type"] = component_type
    if component_type == "chart":
        normalized["props"] = _normalize_chart_props(props, inferred_chart_type=inferred_chart_type)
    elif component_type == "data_table":
        normalized["props"] = _normalize_table_props(props)
    elif component_type == "chat_panel":
        normalized["props"] = _normalize_chat_props(props)
    elif component_type == "button":
        normalized["props"] = _normalize_button_props(props)
    elif component_type == "input":
        normalized["props"] = _normalize_input_props(props)
    elif component_type == "textarea":
        normalized["props"] = _normalize_textarea_props(props)
    elif component_type == "select":
        normalized["props"] = _normalize_select_props(props)
    elif component_type == "checkbox":
        normalized["props"] = _normalize_checkbox_props(props)
    elif component_type == "radio_group":
        normalized["props"] = _normalize_radio_group_props(props)
    elif component_type == "slider":
        normalized["props"] = _normalize_slider_props(props)
    elif component_type == "metric_card":
        normalized["props"] = _normalize_metric_card_props(props)
    elif component_type == "list_view":
        normalized["props"] = _normalize_list_view_props(props)
    elif component_type == "tabs":
        normalized["props"] = _normalize_tabs_props(props)
    elif component_type == "accordion":
        normalized["props"] = _normalize_accordion_props(props)
    elif component_type == "container":
        normalized["props"] = _normalize_container_props(props)
    elif component_type == "image":
        normalized["props"] = _normalize_image_props(props)
    elif component_type == "iframe":
        normalized["props"] = _normalize_iframe_props(props)
    elif component_type == "code_block":
        normalized["props"] = _normalize_code_block_props(props)
    elif component_type == "divider":
        normalized["props"] = _normalize_divider_props(props)
    else:
        normalized["props"] = deepcopy(props)

    return normalized


def normalize_metaui_spec(
    spec: Mapping[str, Any],
    *,
    strict_component_types: bool = False,
) -> Dict[str, Any]:
    normalized = deepcopy(dict(spec))
    if "send_data_model" not in normalized and "sendDataModel" in normalized:
        normalized["send_data_model"] = bool(normalized.get("sendDataModel"))
    normalized["theme"] = _normalize_theme(normalized.get("theme"))
    components = normalized.get("components")
    if isinstance(components, list):
        normalized_components: list[Dict[str, Any]] = []
        for component in components:
            if isinstance(component, Mapping):
                normalized_components.append(
                    normalize_component(component, strict_component_types=strict_component_types)
                )
            else:
                normalized_components.append(component)
        normalized["components"] = normalized_components
    return normalized


def normalize_metaui_patch(
    patch: Mapping[str, Any],
    *,
    strict_component_types: bool = False,
) -> Dict[str, Any]:
    normalized = deepcopy(dict(patch))
    op_raw = normalized.get("op")
    op = _norm_token(op_raw) if op_raw is not None else ""
    if op:
        normalized["op"] = op

    if op in {"replace_spec", "merge_spec"} and isinstance(normalized.get("spec"), Mapping):
        normalized["spec"] = normalize_metaui_spec(
            normalized["spec"],
            strict_component_types=strict_component_types,
        )
        return normalized

    if op == "append_component" and isinstance(normalized.get("component"), Mapping):
        normalized["component"] = normalize_component(
            normalized["component"],
            strict_component_types=strict_component_types,
        )
        return normalized

    if op == "update_component":
        component_patch = normalized.get("component")
        if isinstance(component_patch, Mapping):
            component_payload = normalize_component(
                component_patch,
                strict_component_types=strict_component_types,
            )
            normalized.setdefault("id", component_payload.get("id"))
            merged_props = dict(component_payload.get("props") or {})
            if isinstance(normalized.get("props"), Mapping):
                merged_props.update(dict(normalized["props"]))
            normalized["props"] = merged_props
            if component_payload.get("type"):
                normalized["type"] = component_payload["type"]

        raw_type = normalized.get("type")
        if raw_type is not None:
            component_type, inferred_chart_type = _normalize_component_type(raw_type)
            if strict_component_types and component_type not in UI_COMPONENT_TYPES:
                raise ValueError(
                    f"Unsupported component type: {component_type}. Allowed: {sorted(UI_COMPONENT_TYPES)}"
                )
            normalized["type"] = component_type
            if component_type == "chart":
                props = normalized.get("props") if isinstance(normalized.get("props"), Mapping) else {}
                normalized["props"] = _normalize_chart_props(
                    props,
                    inferred_chart_type=inferred_chart_type,
                )
        return normalized

    if "components" in normalized and isinstance(normalized.get("components"), list):
        return normalize_metaui_spec(
            normalized,
            strict_component_types=strict_component_types,
        )
    return normalized
