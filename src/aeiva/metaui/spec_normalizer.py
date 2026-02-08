from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

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

_INTERACTION_EVENT_HINTS: Dict[str, Tuple[str, ...]] = {
    "tabs": ("change",),
    "accordion": ("change",),
    "button": ("action", "click"),
    "input": ("change", "submit"),
    "textarea": ("change",),
    "select": ("change",),
    "checkbox": ("change",),
    "radio_group": ("change",),
    "slider": ("change",),
    "file_uploader": ("upload", "change"),
    "form": ("submit", "change"),
    "chat_panel": ("submit", "change"),
    "form_step": ("submit", "change"),
    "result_export": ("export", "action"),
}

_LOCAL_ACTION_STEP_TOKENS = {
    "sequence",
    "set_state",
    "merge_state",
    "append_state",
    "mutate",
    "emit_event",
    "emit",
    "notify",
    "toast",
    "spec_patch",
    "apply_patch",
    "patch",
    "run_action",
    "call_action",
    "merge_theme",
    "set_theme",
    "append_chat_message",
    "chat_append",
    "add_message",
    "clear_chat",
    "chat_clear",
    "clear_messages",
}

_THEME_DARK_PRESET: Dict[str, Any] = {
    "color_bg_top": "#0f172a",
    "color_bg_bottom": "#111827",
    "color_surface": "#1f2937",
    "color_text": "#e5e7eb",
    "color_muted": "#9ca3af",
    "color_border": "#334155",
    "color_border_strong": "#475569",
    "color_primary": "#22d3ee",
    "color_primary_hover": "#06b6d4",
    "color_primary_soft": "#164e63",
    "color_focus_ring": "rgba(34, 211, 238, 0.35)",
}

_THEME_LIGHT_PRESET: Dict[str, Any] = {
    "color_bg_top": "#f4f8ff",
    "color_bg_bottom": "#edf2f8",
    "color_surface": "#ffffff",
    "color_text": "#0f172a",
    "color_muted": "#64748b",
    "color_border": "#d6dde8",
    "color_border_strong": "#c2cedd",
    "color_primary": "#0f766e",
    "color_primary_hover": "#0b5f59",
    "color_primary_soft": "#dff6f4",
    "color_focus_ring": "rgba(15, 118, 110, 0.25)",
}


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
        out: list[str] = []
        for item in raw_children:
            ref = _coerce_component_ref(item)
            if ref:
                out.append(ref)
        return out
    if raw_child is None:
        return []
    ref = _coerce_component_ref(raw_child)
    return [ref] if ref else []


def _coerce_component_ref(raw: Any) -> Optional[str]:
    if isinstance(raw, Mapping):
        return None
    if isinstance(raw, (list, tuple, set)):
        return None
    token = str(raw or "").strip()
    return token or None


def _next_generated_component_id(existing_ids: set[str], *, prefix: str) -> str:
    token = _norm_token(prefix) or "component"
    index = 1
    while True:
        candidate = f"{token}_{index}"
        if candidate not in existing_ids:
            existing_ids.add(candidate)
            return candidate
        index += 1


def _claim_component_id(existing_ids: set[str], raw_id: Any, *, preferred_prefix: str) -> str:
    candidate = str(raw_id or "").strip()
    if candidate and candidate not in existing_ids:
        existing_ids.add(candidate)
        return candidate
    return _next_generated_component_id(existing_ids, prefix=preferred_prefix)


def _collect_child_component_ids(
    raw_children: Any,
    *,
    add_component: Callable[[Mapping[str, Any], str], Optional[str]],
    hint_prefix: str,
) -> list[str]:
    children: list[str] = []
    if not isinstance(raw_children, list):
        return children
    for index, child in enumerate(raw_children):
        if isinstance(child, Mapping):
            child_id = add_component(child, f"{hint_prefix}_{index + 1}")
            if child_id:
                children.append(child_id)
            continue
        child_id = _coerce_component_ref(child)
        if child_id:
            children.append(child_id)
    return children


def _expand_inline_component_refs(
    raw_component: Mapping[str, Any],
    props: Dict[str, Any],
    *,
    add_component: Callable[[Mapping[str, Any], str], Optional[str]],
    hint_prefix: str,
) -> None:
    component_type, _ = _normalize_component_type(_component_raw_type(raw_component))
    if component_type == "container":
        raw_children = props.get("children")
        if not isinstance(raw_children, list):
            raw_child = props.get("child")
            raw_children = [raw_child] if raw_child is not None else []
        props["children"] = _collect_child_component_ids(
            raw_children,
            add_component=add_component,
            hint_prefix=f"{hint_prefix}_child",
        )
        return

    if component_type == "tabs":
        normalized_tabs: list[Dict[str, Any]] = []
        for index, tab in enumerate(props.get("tabs") if isinstance(props.get("tabs"), list) else []):
            if not isinstance(tab, Mapping):
                continue
            tab_payload = deepcopy(dict(tab))
            raw_children = tab_payload.get("children")
            if not isinstance(raw_children, list):
                raw_child = tab_payload.get("child")
                raw_children = [raw_child] if raw_child is not None else []
            tab_payload["children"] = _collect_child_component_ids(
                raw_children,
                add_component=add_component,
                hint_prefix=f"{hint_prefix}_tab_{index + 1}_child",
            )
            normalized_tabs.append(tab_payload)
        props["tabs"] = normalized_tabs
        return

    if component_type == "accordion":
        normalized_sections: list[Dict[str, Any]] = []
        for index, section in enumerate(
            props.get("sections") if isinstance(props.get("sections"), list) else []
        ):
            if not isinstance(section, Mapping):
                continue
            section_payload = deepcopy(dict(section))
            raw_children = section_payload.get("children")
            if not isinstance(raw_children, list):
                raw_child = section_payload.get("child")
                raw_children = [raw_child] if raw_child is not None else []
            section_payload["children"] = _collect_child_component_ids(
                raw_children,
                add_component=add_component,
                hint_prefix=f"{hint_prefix}_section_{index + 1}_child",
            )
            normalized_sections.append(section_payload)
        props["sections"] = normalized_sections


def _props_have_inline_component_refs(component_type: str, props: Mapping[str, Any]) -> bool:
    if component_type == "container":
        raw_children = props.get("children")
        if isinstance(raw_children, list) and any(isinstance(item, Mapping) for item in raw_children):
            return True
        return isinstance(props.get("child"), Mapping)

    if component_type == "tabs":
        raw_tabs = props.get("tabs")
        if not isinstance(raw_tabs, list):
            return False
        for tab in raw_tabs:
            if not isinstance(tab, Mapping):
                continue
            children = tab.get("children")
            if isinstance(children, list) and any(isinstance(item, Mapping) for item in children):
                return True
            if isinstance(tab.get("child"), Mapping):
                return True
        return False

    if component_type == "accordion":
        raw_sections = props.get("sections")
        if not isinstance(raw_sections, list):
            return False
        for section in raw_sections:
            if not isinstance(section, Mapping):
                continue
            children = section.get("children")
            if isinstance(children, list) and any(isinstance(item, Mapping) for item in children):
                return True
            if isinstance(section.get("child"), Mapping):
                return True
        return False

    return False


def _normalize_component_graph(
    *,
    seed_components: Sequence[Mapping[str, Any]],
    seed_root_entries: Sequence[Any],
    strict_component_types: bool,
) -> tuple[list[Dict[str, Any]], list[str], list[str]]:
    normalized_components: list[Dict[str, Any]] = []
    existing_ids: set[str] = set()
    preferred_id_aliases: Dict[str, str] = {}
    seed_component_ids: list[str] = []

    def _add_component(raw_component: Mapping[str, Any], hint: str) -> Optional[str]:
        payload = deepcopy(dict(raw_component))
        raw_type = _component_raw_type(payload)
        preferred_prefix = (
            _norm_token(raw_type)
            or _norm_token(payload.get("component"))
            or _norm_token(hint)
            or "component"
        )
        component_id = _claim_component_id(
            existing_ids,
            payload.get("id"),
            preferred_prefix=preferred_prefix,
        )
        payload["id"] = component_id
        raw_id = str(raw_component.get("id") or "").strip()
        if raw_id and raw_id not in preferred_id_aliases:
            preferred_id_aliases[raw_id] = component_id

        props = _extract_component_props(payload)
        _expand_inline_component_refs(
            payload,
            props,
            add_component=_add_component,
            hint_prefix=component_id,
        )

        component_payload: Dict[str, Any] = {"id": component_id, "props": props}
        if payload.get("type") is not None:
            component_payload["type"] = payload["type"]
        elif payload.get("component") is not None:
            component_payload["component"] = payload["component"]
        else:
            component_payload["type"] = "text"

        normalized_components.append(
            normalize_component(
                component_payload,
                strict_component_types=strict_component_types,
            )
        )
        return component_id

    for index, raw_component in enumerate(seed_components):
        component_id = _add_component(raw_component, f"component_{index + 1}")
        if component_id:
            seed_component_ids.append(component_id)

    root_ids: list[str] = []
    seen_root_ids: set[str] = set()
    for index, entry in enumerate(seed_root_entries):
        component_id: Optional[str] = None
        if isinstance(entry, Mapping):
            component_id = _add_component(entry, f"root_{index + 1}")
        else:
            token = str(entry or "").strip()
            if token:
                component_id = preferred_id_aliases.get(token, token)
        if component_id and component_id not in seen_root_ids:
            root_ids.append(component_id)
            seen_root_ids.add(component_id)

    return normalized_components, root_ids, seed_component_ids


def _seed_components_from_raw(raw_components: Any) -> list[Mapping[str, Any]]:
    seed_components: list[Mapping[str, Any]] = []
    if isinstance(raw_components, Mapping):
        if _looks_like_component_object(raw_components):
            return [raw_components]
        for key, value in raw_components.items():
            key_token = str(key or "").strip()
            if isinstance(value, Mapping):
                payload = deepcopy(dict(value))
                if key_token and not str(payload.get("id") or "").strip():
                    payload["id"] = key_token
                seed_components.append(payload)
                continue
            if not key_token:
                continue
            text = str(value).strip() if value is not None else key_token
            seed_components.append(
                {
                    "id": key_token,
                    "type": "text",
                    "props": {"text": text or key_token},
                }
            )
        return seed_components
    if not isinstance(raw_components, list):
        return seed_components
    for item in raw_components:
        if isinstance(item, Mapping):
            seed_components.append(item)
            continue
        token = str(item or "").strip()
        if not token:
            continue
        seed_components.append(
            {
                "id": token,
                "type": "text",
                "props": {"text": token},
            }
        )
    return seed_components


def _looks_like_component_object(raw: Mapping[str, Any]) -> bool:
    keys = set(raw.keys())
    return bool(keys & {"id", "type", "component", "props", "children", "child"})


def _seed_root_entries_from_raw(raw_root: Any) -> list[Any]:
    if isinstance(raw_root, list):
        return list(raw_root)
    if isinstance(raw_root, Mapping):
        return [raw_root]
    scalar = _coerce_component_ref(raw_root)
    if scalar:
        return [scalar]
    return []


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
    if isinstance(messages, Mapping):
        # Preserve declarative state/data-model bindings like {"$state": "messages"}.
        normalized["messages"] = deepcopy(dict(messages))
        messages = []
    elif not isinstance(messages, list):
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


def _normalize_effects(raw: Any) -> list[Dict[str, Any]]:
    """Normalize `effects` into a list of shallow operation maps."""
    if isinstance(raw, list):
        return [deepcopy(dict(item)) for item in raw if isinstance(item, Mapping)]
    if isinstance(raw, Mapping):
        return [deepcopy(dict(raw))]
    return []


def _normalize_event_config(raw: Any) -> Optional[Dict[str, Any]]:
    """Normalize a per-event config block (`on_change`, `events.submit`, etc.)."""
    if isinstance(raw, str):
        action = raw.strip()
        if not action:
            return None
        return {"action": action}
    if isinstance(raw, list):
        steps = [deepcopy(dict(item)) for item in raw if isinstance(item, Mapping)]
        if not steps:
            return None
        return {"steps": steps}
    if not isinstance(raw, Mapping):
        return None
    normalized: Dict[str, Any] = {}
    action = raw.get("action")
    if action is None:
        action = raw.get("action_id")
    if action is None:
        action = raw.get("handler")
    if action is None:
        action = raw.get("command")
    if action is not None:
        action_text = str(action).strip()
        if action_text:
            normalized["action"] = action_text
    event_type = raw.get("event_type")
    if event_type is not None:
        normalized["event_type"] = str(event_type)
    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list):
        steps_raw = raw.get("actions")
    if isinstance(steps_raw, list):
        steps = [deepcopy(dict(item)) for item in steps_raw if isinstance(item, Mapping)]
        if steps:
            normalized["steps"] = steps
    payload = raw.get("payload")
    if isinstance(payload, Mapping):
        normalized["payload"] = deepcopy(dict(payload))
    effects = _normalize_effects(raw.get("effects"))
    if effects:
        normalized["effects"] = effects
    emit_event = raw.get("emit_event")
    if isinstance(emit_event, bool):
        normalized["emit_event"] = bool(emit_event)
    elif isinstance(emit_event, str):
        event_name = emit_event.strip()
        if event_name:
            normalized["emit_event"] = True
            normalized.setdefault("event_type", event_name)
    elif isinstance(emit_event, list):
        first_name = next(
            (str(item).strip() for item in emit_event if str(item).strip()),
            "",
        )
        if first_name:
            normalized["emit_event"] = True
            normalized.setdefault("event_type", first_name)
    target_component_id = raw.get("target_component_id")
    if target_component_id is not None:
        normalized["target_component_id"] = str(target_component_id)
    return normalized


def _canonical_interaction_event_name(
    raw_key: Any,
    *,
    supported_events: Sequence[str],
) -> Optional[str]:
    raw_text = str(raw_key or "").strip()
    if raw_text == "*":
        return "*"
    token = _norm_token(raw_text)
    if not token:
        return None
    supported_lookup = {_norm_token(item): item for item in supported_events}
    if token in supported_lookup:
        return supported_lookup[token]

    candidate = token
    if candidate.startswith("on_"):
        candidate = candidate[3:]
    elif candidate.startswith("on") and len(candidate) > 2:
        candidate = candidate[2:]
    candidate = candidate.lstrip("_")
    if not candidate:
        return None
    if candidate in supported_lookup:
        return supported_lookup[candidate]
    return None


def _normalize_interaction_props(
    props: Mapping[str, Any],
    *,
    supported_events: Sequence[str],
) -> Dict[str, Any]:
    """
    Normalize cross-component interaction contract.

    Supports legacy top-level fields (`event_type`, `payload`) and declarative
    event blocks (`events`, `on_<event>`), plus local effects/emit toggles.
    """
    normalized = deepcopy(dict(props))

    if normalized.get("event_type") is not None:
        normalized["event_type"] = str(normalized.get("event_type"))
    payload = normalized.get("payload")
    if payload is not None:
        normalized["payload"] = deepcopy(dict(payload)) if isinstance(payload, Mapping) else {}
    effects = _normalize_effects(normalized.get("effects"))
    if effects:
        normalized["effects"] = effects
    elif "effects" in normalized:
        normalized.pop("effects", None)
    if normalized.get("emit_event") is not None:
        normalized["emit_event"] = bool(normalized.get("emit_event"))
    if normalized.get("target_component_id") is not None:
        normalized["target_component_id"] = str(normalized.get("target_component_id"))

    supported_lookup = {_norm_token(item): item for item in supported_events}

    events_block = normalized.get("events")
    if isinstance(events_block, Mapping):
        parsed_events: Dict[str, Dict[str, Any]] = {}
        for raw_key, raw_value in events_block.items():
            event_name = _canonical_interaction_event_name(
                raw_key,
                supported_events=supported_events,
            )
            if not event_name:
                continue
            if event_name != "*" and _norm_token(event_name) not in supported_lookup:
                continue
            config = _normalize_event_config(raw_value)
            if config is not None:
                parsed_events[event_name] = config
        if parsed_events:
            normalized["events"] = parsed_events
        else:
            normalized.pop("events", None)
    elif "events" in normalized:
        normalized.pop("events", None)

    normalized_event_handlers: Dict[str, Dict[str, Any]] = {}
    for raw_key in list(normalized.keys()):
        raw_key_text = str(raw_key or "")
        key_token = _norm_token(raw_key_text)
        if not key_token.startswith("on"):
            continue
        event_name = _canonical_interaction_event_name(
            raw_key_text,
            supported_events=supported_events,
        )
        if not event_name or event_name == "*":
            continue
        if _norm_token(event_name) not in supported_lookup:
            continue
        config = _normalize_event_config(normalized.get(raw_key))
        normalized.pop(raw_key, None)
        if config is None:
            continue
        normalized_event_handlers[f"on_{event_name}"] = config

    normalized.update(normalized_event_handlers)

    return normalized


def _collect_declared_action_ids(raw_actions: Any) -> tuple[set[str], set[str]]:
    declared_ids: set[str] = set()
    if isinstance(raw_actions, list):
        for item in raw_actions:
            if not isinstance(item, Mapping):
                continue
            action_id = str(item.get("id") or item.get("name") or "").strip()
            if action_id:
                declared_ids.add(action_id)
    elif isinstance(raw_actions, Mapping):
        for key, value in raw_actions.items():
            key_text = str(key or "").strip()
            if key_text:
                declared_ids.add(key_text)
            if isinstance(value, Mapping):
                action_id = str(value.get("id") or value.get("name") or "").strip()
                if action_id:
                    declared_ids.add(action_id)
    declared_tokens = {_norm_token(item) for item in declared_ids if _norm_token(item)}
    return declared_ids, declared_tokens


def _action_is_declared_or_builtin(
    action_name: str,
    *,
    declared_ids: set[str],
    declared_tokens: set[str],
) -> bool:
    action_text = str(action_name or "").strip()
    if not action_text:
        return False
    if action_text in declared_ids:
        return True
    token = _norm_token(action_text)
    if not token:
        return False
    return token in declared_tokens or token in _LOCAL_ACTION_STEP_TOKENS


def _iter_component_event_configs(
    props: Mapping[str, Any],
    *,
    supported_events: Sequence[str],
) -> list[tuple[str, Dict[str, Any]]]:
    configs: list[tuple[str, Dict[str, Any]]] = []
    supported_lookup = {_norm_token(item): item for item in supported_events}

    events_block = props.get("events")
    if isinstance(events_block, Mapping):
        for raw_key, raw_value in events_block.items():
            event_name = _canonical_interaction_event_name(
                raw_key,
                supported_events=supported_events,
            )
            if not event_name or event_name == "*":
                continue
            if _norm_token(event_name) not in supported_lookup:
                continue
            config = _normalize_event_config(raw_value)
            if config is not None:
                configs.append((event_name, config))

    for raw_key, raw_value in props.items():
        key_token = _norm_token(raw_key)
        if not key_token.startswith("on"):
            continue
        event_name = _canonical_interaction_event_name(
            raw_key,
            supported_events=supported_events,
        )
        if not event_name or event_name == "*":
            continue
        if _norm_token(event_name) not in supported_lookup:
            continue
        config = _normalize_event_config(raw_value)
        if config is not None:
            configs.append((event_name, config))

    # Resolve fallback semantics equivalent to desktop runtime:
    # top-level `action`/`effects`/`emit_event` act as default event config.
    default_event = supported_events[0] if supported_events else "action"
    if "action" in supported_lookup:
        default_event = supported_lookup["action"]
    fallback_cfg: Dict[str, Any] = {}
    action_raw = props.get("action")
    if action_raw is None:
        action_raw = props.get("command")
    if action_raw is None:
        action_raw = props.get("local_action")
    if action_raw is not None:
        action_text = str(action_raw).strip()
        if action_text:
            fallback_cfg["action"] = action_text
    fallback_effects = _normalize_effects(props.get("effects"))
    if fallback_effects:
        fallback_cfg["effects"] = fallback_effects
    if "emit_event" in props:
        fallback_cfg["emit_event"] = bool(props.get("emit_event"))
    if fallback_cfg:
        configs.append((default_event, fallback_cfg))

    return configs


def _validate_event_steps(
    *,
    component_id: str,
    event_name: str,
    steps: Any,
    declared_ids: set[str],
    declared_tokens: set[str],
) -> list[str]:
    if not isinstance(steps, list):
        return []
    issues: list[str] = []
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            continue
        token = _norm_token(step.get("type") or step.get("op") or step.get("action") or step.get("kind"))
        if not token:
            continue
        if token in {"run_action", "call_action"}:
            nested = str(step.get("action_id") or step.get("name") or "").strip()
            if nested and not _action_is_declared_or_builtin(
                nested,
                declared_ids=declared_ids,
                declared_tokens=declared_tokens,
            ):
                issues.append(
                    f"component '{component_id}' event '{event_name}' step[{index}] references unknown action '{nested}'."
                )
            continue
        if token in _LOCAL_ACTION_STEP_TOKENS or token in declared_tokens:
            continue
        issues.append(
            f"component '{component_id}' event '{event_name}' step[{index}] uses unsupported token '{token}'."
        )
    return issues


def collect_interaction_contract_issues(spec: Mapping[str, Any]) -> list[str]:
    """Return declarative interaction contract issues for a normalized MetaUI spec."""
    components = spec.get("components")
    if not isinstance(components, list):
        return ["`components` must be a list."]

    declared_ids, declared_tokens = _collect_declared_action_ids(spec.get("actions"))
    issues: list[str] = []
    for component in components:
        if not isinstance(component, Mapping):
            continue
        component_id = str(component.get("id") or "").strip() or "<unknown>"
        component_type = str(component.get("type") or "").strip()
        supported_events = _INTERACTION_EVENT_HINTS.get(component_type)
        if not supported_events:
            continue
        props = component.get("props")
        if not isinstance(props, Mapping):
            issues.append(f"component '{component_id}' has invalid props for interactive type '{component_type}'.")
            continue

        event_configs = _iter_component_event_configs(
            props,
            supported_events=supported_events,
        )
        for event_name, config in event_configs:
            action_name = str(config.get("action") or "").strip()
            if action_name and not _action_is_declared_or_builtin(
                action_name,
                declared_ids=declared_ids,
                declared_tokens=declared_tokens,
            ):
                issues.append(
                    f"component '{component_id}' event '{event_name}' references unknown action '{action_name}'."
                )
            issues.extend(
                _validate_event_steps(
                    component_id=component_id,
                    event_name=event_name,
                    steps=config.get("steps"),
                    declared_ids=declared_ids,
                    declared_tokens=declared_tokens,
                )
            )
            has_local_behavior = bool(action_name) or bool(config.get("steps")) or bool(config.get("effects"))
            if config.get("emit_event") is False and not has_local_behavior:
                issues.append(
                    f"component '{component_id}' event '{event_name}' disables emit_event but defines no local behavior."
                )

        # Explicitly disabling event emission on interactive components without local behavior is a no-op shell.
        if props.get("emit_event") is False:
            has_default_local_behavior = bool(
                str(props.get("action") or props.get("command") or props.get("local_action") or "").strip()
            ) or bool(_normalize_effects(props.get("effects")))
            if not has_default_local_behavior and not event_configs:
                issues.append(
                    f"component '{component_id}' disables emit_event and has no event/action/effects configuration."
                )

    return issues


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
    effects = _normalize_effects(normalized.get("effects"))
    if effects:
        normalized["effects"] = effects
    elif "effects" in normalized:
        normalized.pop("effects", None)
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
            children: list[str] = []
            raw_children = item.get("children")
            if isinstance(raw_children, list):
                for child in raw_children:
                    ref = _coerce_component_ref(child)
                    if ref:
                        children.append(ref)
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
            children: list[str] = []
            raw_children = item.get("children")
            if isinstance(raw_children, list):
                for child in raw_children:
                    ref = _coerce_component_ref(child)
                    if ref:
                        children.append(ref)
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
        refs: list[str] = []
        for item in children:
            ref = _coerce_component_ref(item)
            if ref:
                refs.append(ref)
        normalized["children"] = refs
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
    if isinstance(theme, str):
        mode = _norm_token(theme)
        if mode in {"dark", "night"}:
            return deepcopy(_THEME_DARK_PRESET)
        if mode in {"light", "day"}:
            return deepcopy(_THEME_LIGHT_PRESET)
        return {}
    if not isinstance(theme, Mapping):
        return {}
    normalized: Dict[str, Any] = {}
    mode_raw = theme.get("mode")
    if mode_raw is None:
        mode_raw = theme.get("scheme")
    if mode_raw is None:
        mode_raw = theme.get("appearance")
    mode = _norm_token(mode_raw)
    if mode in {"dark", "night"}:
        normalized.update(deepcopy(_THEME_DARK_PRESET))
    elif mode in {"light", "day"}:
        normalized.update(deepcopy(_THEME_LIGHT_PRESET))
    for raw_key, raw_value in theme.items():
        key = _norm_token(raw_key)
        if not key:
            continue
        if key in {"mode", "scheme", "appearance"}:
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

    interaction_events = _INTERACTION_EVENT_HINTS.get(component_type)
    if interaction_events:
        normalized["props"] = _normalize_interaction_props(
            normalized["props"],
            supported_events=interaction_events,
        )

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
    seed_components = _seed_components_from_raw(normalized.get("components"))
    seed_root_entries = _seed_root_entries_from_raw(normalized.get("root"))

    normalized_components, normalized_root, seed_component_ids = _normalize_component_graph(
        seed_components=seed_components,
        seed_root_entries=seed_root_entries,
        strict_component_types=strict_component_types,
    )

    component_ids = [
        str(item.get("id") or "").strip()
        for item in normalized_components
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    ]

    if not normalized_components:
        fallback_component = normalize_component(
            {
                "id": "workspace_info",
                "type": "text",
                "props": {
                    "title": "Workspace",
                    "text": "No renderable components were provided.",
                    "card": True,
                },
            },
            strict_component_types=strict_component_types,
        )
        normalized_components = [fallback_component]
        normalized_root = [fallback_component["id"]]
    elif not normalized_root:
        preferred_root_ids: list[str] = []
        seen_preferred_root_ids: set[str] = set()
        for component_id in seed_component_ids:
            if component_id in component_ids and component_id not in seen_preferred_root_ids:
                preferred_root_ids.append(component_id)
                seen_preferred_root_ids.add(component_id)
        normalized_root = preferred_root_ids or component_ids

    normalized["components"] = normalized_components
    normalized["root"] = normalized_root
    return normalized


def _normalize_partial_spec_fragment(
    spec: Mapping[str, Any],
    *,
    strict_component_types: bool = False,
) -> Dict[str, Any]:
    normalized = deepcopy(dict(spec))
    if "send_data_model" not in normalized and "sendDataModel" in normalized:
        normalized["send_data_model"] = bool(normalized.get("sendDataModel"))
    if "theme" in normalized:
        normalized["theme"] = _normalize_theme(normalized.get("theme"))

    has_components = "components" in normalized
    has_root = "root" in normalized
    raw_root = normalized.get("root")
    root_is_component_mapping = isinstance(raw_root, Mapping)
    root_list_has_component_mappings = isinstance(raw_root, list) and any(
        isinstance(item, Mapping) for item in raw_root
    )

    if has_components or root_is_component_mapping or root_list_has_component_mappings:
        seed_components = _seed_components_from_raw(normalized.get("components")) if has_components else []
        seed_root_entries = _seed_root_entries_from_raw(raw_root) if has_root else []
        normalized_components, normalized_root, _ = _normalize_component_graph(
            seed_components=seed_components,
            seed_root_entries=seed_root_entries,
            strict_component_types=strict_component_types,
        )
        if has_components or normalized_components:
            normalized["components"] = normalized_components
        if has_root:
            normalized["root"] = normalized_root
        elif "root" in normalized:
            normalized.pop("root", None)
        return normalized

    if has_root:
        if isinstance(raw_root, list):
            normalized["root"] = [str(item) for item in raw_root if str(item).strip()]
        else:
            normalized.pop("root", None)
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

    if op == "replace_spec" and isinstance(normalized.get("spec"), Mapping):
        normalized["spec"] = normalize_metaui_spec(
            normalized["spec"],
            strict_component_types=strict_component_types,
        )
        return normalized

    if op == "merge_spec" and isinstance(normalized.get("spec"), Mapping):
        normalized["spec"] = _normalize_partial_spec_fragment(
            normalized["spec"],
            strict_component_types=strict_component_types,
        )
        return normalized

    if op == "append_component" and isinstance(normalized.get("component"), Mapping):
        expanded_components, _, seed_component_ids = _normalize_component_graph(
            seed_components=[normalized["component"]],
            seed_root_entries=[],
            strict_component_types=strict_component_types,
        )
        if len(expanded_components) == 1:
            normalized["component"] = expanded_components[0]
            return normalized
        return {
            "op": "merge_spec",
            "spec": {
                "components": expanded_components,
            },
            "expanded_from": "append_component",
            "primary_component_id": seed_component_ids[0] if seed_component_ids else None,
        }

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
            props = normalized.get("props")
            has_inline_refs = isinstance(props, Mapping) and _props_have_inline_component_refs(component_type, props)
            if has_inline_refs and normalized.get("id") is not None:
                expanded_components, _, seed_component_ids = _normalize_component_graph(
                    seed_components=[
                        {
                            "id": normalized.get("id"),
                            "type": component_type,
                            "props": props,
                        }
                    ],
                    seed_root_entries=[],
                    strict_component_types=strict_component_types,
                )
                if len(expanded_components) > 1:
                    return {
                        "op": "merge_spec",
                        "spec": {
                            "components": expanded_components,
                        },
                        "expanded_from": "update_component",
                        "primary_component_id": seed_component_ids[0] if seed_component_ids else None,
                    }
            if isinstance(props, Mapping):
                synthetic_id = str(normalized.get("id") or "patch_component")
                normalized_component = normalize_component(
                    {
                        "id": synthetic_id,
                        "type": component_type,
                        "props": props,
                    },
                    strict_component_types=strict_component_types,
                )
                normalized["props"] = deepcopy(dict(normalized_component.get("props") or {}))
                if component_type == "chart" and inferred_chart_type:
                    normalized["props"]["chart_type"] = inferred_chart_type
            elif props is not None:
                normalized["props"] = {}
        return normalized

    if op == "set_root":
        raw_root = normalized.get("root")
        seed_root_entries = _seed_root_entries_from_raw(raw_root)
        if any(isinstance(item, Mapping) for item in seed_root_entries):
            expanded_components, normalized_root, _ = _normalize_component_graph(
                seed_components=[],
                seed_root_entries=seed_root_entries,
                strict_component_types=strict_component_types,
            )
            patch_spec: Dict[str, Any] = {"root": normalized_root}
            if expanded_components:
                patch_spec["components"] = expanded_components
            return {
                "op": "merge_spec",
                "spec": patch_spec,
                "expanded_from": "set_root",
            }
        normalized["root"] = [ref for ref in (_coerce_component_ref(item) for item in seed_root_entries) if ref]
        return normalized

    if "components" in normalized and isinstance(normalized.get("components"), list):
        return normalize_metaui_spec(
            normalized,
            strict_component_types=strict_component_types,
        )
    return normalized
