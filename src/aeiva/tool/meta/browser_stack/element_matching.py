"""Element matching heuristics for BrowserService snapshot resolution."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .value_utils import _as_str
from .element_node_utils import (
    _build_node_haystack,
    _compact_node_match,
    _contains_hint_token,
    _looks_like_date_literal,
    _node_has_nonempty_value,
    _node_is_clickable,
    _node_is_disabled,
    _node_is_editable,
    _node_is_readonly,
    _node_looks_negative_action,
)


def _find_scroll_recovery_refs(nodes: list[Any], *, max_results: int = 8) -> list[Dict[str, Any]]:
    keywords = (
        "done",
        "confirm",
        "apply",
        "search",
        "ok",
        "continue",
        "next",
        "submit",
        "完成",
        "确认",
        "确定",
        "应用",
        "搜索",
        "继续",
        "下一步",
        "提交",
    )
    ranked: list[tuple[int, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ref = _as_str(node.get("ref"))
        if not ref:
            continue
        haystack = _build_node_haystack(node)
        if not haystack:
            continue
        score = 0
        for token in keywords:
            if token in haystack:
                score += 10
        if score == 0:
            continue
        role = _as_str(node.get("role")) or ""
        if role in {"button", "option", "link", "menuitem"}:
            score += 6
        disabled_text = (_as_str(node.get("disabled")) or "").lower()
        if disabled_text in {"true", "1"}:
            score -= 20
        ranked.append((score, _compact_node_match(node)))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in ranked[:max_results]]


def _find_click_target_candidates_from_nodes(
    nodes: list[Any],
    *,
    query_text: str,
    max_results: int = 3,
) -> list[Dict[str, Any]]:
    clean = (query_text or "").strip().casefold()
    if not clean:
        return []
    tokens = [token for token in clean.split() if token]
    if not tokens:
        return []

    ranked: list[tuple[int, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ref = _as_str(node.get("ref"))
        if not ref:
            continue
        if _node_is_disabled(node):
            continue
        if not _node_is_clickable(node):
            continue

        haystack = _build_node_haystack(node)
        if not haystack:
            continue

        score = 0
        if clean in haystack:
            score += 90
        elif all(token in haystack for token in tokens):
            score += 60
        else:
            continue

        name = str(node.get("name") or "").strip().casefold()
        text = str(node.get("text") or "").strip().casefold()
        if name == clean or text == clean:
            score += 25
        if clean in name or clean in text:
            score += 10

        role = str(node.get("role") or "").strip().casefold()
        if role in {"button", "option", "link", "menuitem", "tab"}:
            score += 6
        if _node_looks_negative_action(node):
            score -= 30

        ranked.append((score, _compact_node_match(node)))

    if not ranked:
        return []
    ranked.sort(key=lambda item: item[0], reverse=True)
    out: list[Dict[str, Any]] = []
    for score, item in ranked:
        if score <= 0:
            continue
        out.append(item)
        if len(out) >= max(1, int(max_results)):
            break
    return out


def _find_click_target_from_nodes(nodes: list[Any], *, query_text: str) -> Optional[Dict[str, Any]]:
    candidates = _find_click_target_candidates_from_nodes(
        nodes,
        query_text=query_text,
        max_results=1,
    )
    return candidates[0] if candidates else None


def _find_confirm_target_from_nodes(
    nodes: list[Any],
    *,
    preferred_text: Optional[str] = None,
    context: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    context_text = (context or "").strip().casefold()
    preferred_clean = (preferred_text or "").strip()
    preferred_is_date = _looks_like_date_literal(preferred_clean)
    date_context = (
        "date" in context_text
        or "calendar" in context_text
        or context_text in {"date_picker", "set_date", "date_confirm"}
        or preferred_is_date
    )

    if preferred_clean and not date_context:
        matched = _find_click_target_from_nodes(nodes, query_text=preferred_text)
        if matched is not None and not _node_looks_negative_action(matched):
            return matched

    ranked: list[tuple[int, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ref = _as_str(node.get("ref"))
        if not ref:
            continue
        if _node_is_disabled(node):
            continue
        if not _node_is_clickable(node):
            continue

        haystack = _build_node_haystack(node)
        if not haystack:
            continue
        score = 0
        for token in _CONFIRM_KEYWORDS:
            if token in haystack:
                score += 12
        if score == 0:
            continue
        date_confirm_hits = sum(1 for token in _DATE_CONFIRM_KEYWORDS if token in haystack)
        search_action_hits = sum(1 for token in _SEARCH_ACTION_KEYWORDS if token in haystack)
        if date_context:
            # In date pickers, "Done/Apply/OK" should outrank generic "Search/Filter".
            score += date_confirm_hits * 14
            score -= search_action_hits * 18
        else:
            score += date_confirm_hits * 6
        role = str(node.get("role") or "").strip().casefold()
        if role in {"button", "option", "menuitem"}:
            score += 6
        if _node_looks_negative_action(node):
            score -= 50
        ranked.append((score, _compact_node_match(node)))

    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best = ranked[0]
    if best_score <= 0:
        return None
    return best


def _find_type_target_from_nodes(
    nodes: list[Any],
    *,
    value_text: str,
    field_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    ranked = _rank_type_targets_from_nodes(
        nodes=nodes,
        value_text=value_text,
        field_hint=field_hint,
    )
    if not ranked:
        return None
    best_score, best = ranked[0]
    if best_score <= 0:
        return None
    return best


def _find_type_target_candidates_from_nodes(
    nodes: list[Any],
    *,
    value_text: str,
    field_hint: Optional[str] = None,
    max_results: int = 3,
) -> list[Dict[str, Any]]:
    ranked = _rank_type_targets_from_nodes(
        nodes=nodes,
        value_text=value_text,
        field_hint=field_hint,
    )
    limit = max(1, int(max_results))
    out: list[Dict[str, Any]] = []
    for score, item in ranked:
        if score <= 0:
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _rank_type_targets_from_nodes(
    *,
    nodes: list[Any],
    value_text: str,
    field_hint: Optional[str],
) -> list[tuple[int, Dict[str, Any]]]:
    value = (value_text or "").strip()
    if not value:
        return []

    clean_field = (field_hint or "").strip().casefold()
    field_tokens = [token for token in clean_field.split() if token]
    intent = _infer_input_intent(value)

    ranked: list[tuple[int, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ref = _as_str(node.get("ref"))
        if not ref:
            continue
        if _node_is_disabled(node) or _node_is_readonly(node):
            continue

        haystack = _build_node_haystack(node)
        role = str(node.get("role") or "").strip().casefold()
        input_type = str(node.get("input_type") or "").strip().casefold()
        tag = str(node.get("tag") or "").strip().casefold()
        editable = _node_is_editable(node)
        clickable = _node_is_clickable(node)
        has_aria_numeric = bool(_as_str(node.get("aria_valuenow")))
        date_hint = any(token in haystack for token in _DATE_HINT_TOKENS)
        numeric_control = role == "spinbutton" or input_type in {"number", "range"} or has_aria_numeric
        date_control = input_type in {"date", "datetime-local", "time"} or date_hint

        can_target = editable
        if not can_target:
            if intent == "numeric":
                can_target = clickable and numeric_control
            elif intent == "date":
                can_target = clickable and date_control
            elif intent == "text":
                # Generic combobox wrappers are often clickable instead of directly editable.
                can_target = clickable and role in {"combobox", "button"} and bool(field_tokens)
        if not can_target:
            continue

        score = 0
        has_value = _node_has_nonempty_value(node)

        if role in {"combobox", "textbox", "searchbox", "spinbutton"}:
            score += 10
        if not editable and can_target:
            score += 8
        if not has_value:
            score += 6

        direct_text_control = (
            role in {"textbox", "searchbox", "spinbutton"}
            or tag in {"input", "textarea", "select"}
            or input_type
            in {
                "text",
                "search",
                "email",
                "url",
                "tel",
                "password",
                "number",
                "date",
                "datetime-local",
                "time",
                "month",
                "week",
            }
        )
        if intent in {"text", "airport"}:
            if direct_text_control:
                score += 12
            elif role == "combobox":
                # Combobox containers often wrap the actual editable input.
                # Prefer concrete text controls to avoid typing into wrappers.
                score -= 12

        if clean_field:
            if len(clean_field) > 2 and clean_field in haystack:
                score += 40
            elif field_tokens and all(_contains_hint_token(haystack, token) for token in field_tokens):
                score += 20

        if intent == "numeric":
            if numeric_control:
                score += 18
        elif intent == "date":
            if date_control:
                score += 16
            if date_hint:
                score += 8

        ranked.append((score, _compact_node_match(node)))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def _find_select_target_from_nodes(
    nodes: list[Any],
    *,
    values: list[str],
    field_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    ranked = _rank_select_targets_from_nodes(
        nodes=nodes,
        values=values,
        field_hint=field_hint,
    )
    if not ranked:
        return None
    best_score, best = ranked[0]
    if best_score <= 0:
        return None
    return best


def _find_select_target_candidates_from_nodes(
    nodes: list[Any],
    *,
    values: list[str],
    field_hint: Optional[str] = None,
    max_results: int = 3,
) -> list[Dict[str, Any]]:
    ranked = _rank_select_targets_from_nodes(
        nodes=nodes,
        values=values,
        field_hint=field_hint,
    )
    limit = max(1, int(max_results))
    out: list[Dict[str, Any]] = []
    for score, item in ranked:
        if score <= 0:
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _rank_select_targets_from_nodes(
    *,
    nodes: list[Any],
    values: list[str],
    field_hint: Optional[str],
) -> list[tuple[int, Dict[str, Any]]]:
    clean_field = (field_hint or "").strip().casefold()
    field_tokens = [token for token in clean_field.split() if token]
    value_tokens = [str(v).strip().casefold() for v in values if str(v).strip()]

    ranked: list[tuple[int, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ref = _as_str(node.get("ref"))
        if not ref:
            continue
        if _node_is_disabled(node) or _node_is_readonly(node):
            continue
        role = str(node.get("role") or "").strip().casefold()
        selectable_role = role in {"select", "combobox", "listbox", "option"}
        if not (selectable_role or _node_is_clickable(node) or _node_is_editable(node)):
            continue

        haystack = _build_node_haystack(node)
        if not haystack:
            continue
        score = 0
        has_value = _node_has_nonempty_value(node)
        if role in {"select", "combobox", "listbox"}:
            score += 24
        elif role in {"option", "menuitem"}:
            score += 16
        elif role in {"button", "textbox", "searchbox"}:
            score += 8

        if clean_field:
            if len(clean_field) > 2 and clean_field in haystack:
                score += 36
            elif field_tokens and all(_contains_hint_token(haystack, token) for token in field_tokens):
                score += 18

        if value_tokens and all(_contains_hint_token(haystack, token) for token in value_tokens):
            score += 8

        if not clean_field and has_value:
            score -= 10

        if _node_looks_negative_action(node):
            score -= 35

        ranked.append((score, _compact_node_match(node)))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def _find_editable_recovery_refs(nodes: list[Any], *, max_results: int = 8) -> list[Dict[str, Any]]:
    ranked: list[tuple[int, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        ref = _as_str(node.get("ref"))
        if not ref:
            continue
        if _node_is_disabled(node) or _node_is_readonly(node):
            continue
        if not _node_is_editable(node):
            continue
        haystack = _build_node_haystack(node)
        score = 0
        role = str(node.get("role") or "").strip().casefold()
        input_type = str(node.get("input_type") or "").strip().casefold()
        if role in {"combobox", "textbox", "searchbox", "spinbutton"}:
            score += 8
        if input_type in {"date", "datetime-local", "number", "range"}:
            score += 5
        if _node_has_nonempty_value(node):
            score -= 3
        ranked.append((score, _compact_node_match(node)))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in ranked[:max_results]]


def _pick_editable_recovery_ref(refs: list[Any]) -> Optional[str]:
    for item in refs:
        if not isinstance(item, dict):
            continue
        ref = _as_str(item.get("ref"))
        if not ref:
            continue
        if _node_is_disabled(item) or _node_is_readonly(item):
            continue
        if _node_is_editable(item):
            return ref
    return None


def _pick_confirm_recovery_ref(refs: list[Any]) -> Optional[str]:
    ranked: list[tuple[int, str]] = []
    for item in refs:
        if not isinstance(item, dict):
            continue
        ref = _as_str(item.get("ref"))
        if not ref:
            continue
        if _node_is_disabled(item):
            continue
        haystack = _build_node_haystack(item)
        if not haystack:
            continue
        score = 0
        for token in _CONFIRM_KEYWORDS:
            if token in haystack:
                score += 10
        role = str(item.get("role") or "").strip().casefold()
        if role in {"button", "option", "menuitem"}:
            score += 5
        if _node_looks_negative_action(item):
            score -= 40
        if score > 0:
            ranked.append((score, ref))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def _match_snapshot_nodes(nodes: list[Any], query: str, *, max_results: int = 20) -> list[Dict[str, Any]]:
    clean = (query or "").strip().casefold()
    if not clean:
        return []

    tokens = [token for token in clean.split() if token]
    ranked: list[tuple[int, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        haystack = _build_node_haystack(node)
        if not haystack:
            continue

        if clean in haystack:
            score = 100
        elif tokens and all(token in haystack for token in tokens):
            score = 70
        else:
            continue

        if clean in str(node.get("name", "")).casefold():
            score += 15
        if clean in str(node.get("text", "")).casefold():
            score += 8

        ranked.append((score, _compact_node_match(node)))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in ranked[:max_results]]


def _is_stale_target_error(exc: Exception) -> bool:
    text = str(exc or "").strip().casefold()
    if not text:
        return False
    tokens = (
        "stale",
        "not attached",
        "detached",
        "element is not attached",
        "no node found",
        "unable to resolve locator",
        "locator",
    )
    return any(token in text for token in tokens)


def _infer_input_intent(value_text: str) -> str:
    clean = (value_text or "").strip().casefold()
    if not clean:
        return "text"
    if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", clean):
        return "date"
    if re.search(r"\d", clean):
        return "numeric"
    return "text"


_CONFIRM_KEYWORDS = {
    "done",
    "confirm",
    "apply",
    "search",
    "ok",
    "continue",
    "next",
    "完成",
    "确认",
    "确定",
    "应用",
    "搜索",
    "继续",
    "下一步",
}
_DATE_CONFIRM_KEYWORDS = {
    "done",
    "apply",
    "ok",
    "confirm",
    "save",
    "complete",
    "finish",
    "完成",
    "确认",
    "确定",
    "保存",
}
_SEARCH_ACTION_KEYWORDS = {
    "search",
    "find",
    "filter",
    "book",
    "submit",
    "搜索",
    "筛选",
    "预订",
    "提交",
}
_DATE_HINT_TOKENS = {"date", "day", "depart", "departure", "return", "日期", "时间", "出发"}
_FILL_FIELDS_STEP_OPERATIONS = (
    "type",
    "fill",
    "set_number",
    "set_date",
    "open",
    "navigate",
    "search",
    "back",
    "forward",
    "reload",
    "snapshot",
    "select",
    "choose_option",
    "confirm",
    "submit",
    "click",
    "press",
    "hover",
    "drag",
    "upload",
    "scroll",
    "wait",
    "evaluate",
    "close",
)
