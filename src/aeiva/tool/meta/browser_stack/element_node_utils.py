"""Node-level helper functions for element matching heuristics."""

from __future__ import annotations

import re
from typing import Any, Dict

_CLICKABLE_ROLES = {"button", "link", "option", "menuitem", "tab", "checkbox", "radio"}
_EDITABLE_ROLES = {"input", "textarea", "select", "textbox", "searchbox", "combobox", "spinbutton"}
_NEGATIVE_ACTION_TOKENS = {
    "cancel",
    "close",
    "dismiss",
    "clear",
    "reset",
    "back",
    "取消",
    "关闭",
    "清除",
    "重置",
    "返回",
}


def _build_node_haystack(node: Dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "ref",
        "tag",
        "role",
        "name",
        "label_text",
        "name_attr",
        "dom_id",
        "text",
        "value",
        "aria_label",
        "aria_valuenow",
        "placeholder",
        "input_type",
        "selector",
        "fallback_selector",
    ):
        value = node.get(key)
        if value is None:
            continue
        text = str(value).strip().casefold()
        if text:
            parts.append(text)
    return " ".join(parts)


def _compact_node_match(node: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "ref": node.get("ref"),
        "tag": node.get("tag"),
        "role": node.get("role"),
        "name": node.get("name"),
        "label_text": node.get("label_text"),
        "name_attr": node.get("name_attr"),
        "dom_id": node.get("dom_id"),
        "text": node.get("text"),
        "selector": node.get("selector"),
    }
    for optional_key in ("value", "aria_valuenow", "placeholder", "input_type", "scope"):
        if optional_key in node:
            payload[optional_key] = node.get(optional_key)
    return payload


def _contains_hint_token(haystack: str, token: str) -> bool:
    clean_token = (token or "").strip().casefold()
    if not clean_token:
        return False
    if len(clean_token) <= 2 and clean_token.isascii():
        return re.search(rf"\b{re.escape(clean_token)}\b", haystack) is not None
    return clean_token in haystack


def _looks_like_date_literal(value_text: str) -> bool:
    clean = (value_text or "").strip().casefold()
    if not clean:
        return False
    return re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", clean) is not None


def _node_is_clickable(node: Dict[str, Any]) -> bool:
    role = str(node.get("role") or "").strip().casefold()
    if role in _CLICKABLE_ROLES:
        return True
    selector = str(node.get("selector") or "").casefold()
    if "button" in selector:
        return True
    return False


def _node_looks_negative_action(node: Dict[str, Any]) -> bool:
    haystack = _build_node_haystack(node)
    return any(token in haystack for token in _NEGATIVE_ACTION_TOKENS)


def _node_is_disabled(node: Dict[str, Any]) -> bool:
    value = node.get("disabled")
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _node_is_readonly(node: Dict[str, Any]) -> bool:
    value = node.get("readonly")
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _node_is_editable(node: Dict[str, Any]) -> bool:
    input_type = str(node.get("input_type") or "").strip().casefold()
    if input_type == "hidden":
        return False
    role = str(node.get("role") or "").strip().casefold()
    if role in _EDITABLE_ROLES:
        return True
    if input_type in {
        "text",
        "search",
        "email",
        "url",
        "tel",
        "password",
        "number",
        "range",
        "date",
        "datetime-local",
        "time",
        "month",
        "week",
        "file",
    }:
        return True
    selector = str(node.get("selector") or "").casefold()
    fallback = str(node.get("fallback_selector") or "").casefold()
    haystack = f"{selector} {fallback}"
    return any(token in haystack for token in ("input", "textarea", "select", "combobox", "spinbutton"))


def _node_has_nonempty_value(node: Dict[str, Any]) -> bool:
    value = str(node.get("value") or "").strip()
    if value:
        return True
    aria_now = str(node.get("aria_valuenow") or "").strip()
    return bool(aria_now)
