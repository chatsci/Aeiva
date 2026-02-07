"""Element matching heuristics for BrowserService snapshot resolution."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


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
    field_intent = _infer_field_intent(field_hint)

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
        baggage_hint = any(token in haystack for token in _BAGGAGE_HINT_TOKENS)
        date_hint = any(token in haystack for token in _DATE_HINT_TOKENS)
        destination_hint = any(token in haystack for token in _DESTINATION_HINT_TOKENS)
        origin_hint = any(token in haystack for token in _ORIGIN_HINT_TOKENS)
        departure_date_hint = any(token in haystack for token in _DEPARTURE_DATE_HINT_TOKENS)
        return_date_hint = any(token in haystack for token in _RETURN_DATE_HINT_TOKENS)
        passenger_hint = any(token in haystack for token in _PASSENGER_HINT_TOKENS)
        numeric_control = role == "spinbutton" or input_type in {"number", "range"} or has_aria_numeric
        date_control = input_type in {"date", "datetime-local", "time"} or date_hint

        can_target = editable
        if not can_target:
            if intent == "baggage":
                can_target = clickable and (numeric_control or baggage_hint)
            elif intent == "numeric":
                can_target = clickable and numeric_control
            elif intent == "date":
                can_target = clickable and date_control
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

        if field_intent == "destination":
            if destination_hint:
                score += 24
            if origin_hint:
                score -= 28
        elif field_intent == "origin":
            if origin_hint:
                score += 24
            if destination_hint:
                score -= 20
        elif field_intent == "departure_date":
            if departure_date_hint:
                score += 20
            if return_date_hint:
                score -= 24
        elif field_intent == "return_date":
            if return_date_hint:
                score += 20
            if departure_date_hint:
                score -= 18
        elif field_intent == "baggage":
            if baggage_hint or numeric_control:
                score += 14
            if passenger_hint:
                score -= 10
        elif field_intent == "passengers":
            if passenger_hint:
                score += 18
            if baggage_hint:
                score -= 12

        if intent == "baggage":
            if numeric_control:
                score += 20
            if baggage_hint:
                score += 18
        elif intent == "numeric":
            if numeric_control:
                score += 18
        elif intent == "date":
            if date_control:
                score += 16
            if date_hint:
                score += 10
        elif intent == "airport":
            if destination_hint:
                score += 16
            if origin_hint:
                score -= 8
            if has_value:
                score -= 4

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
    field_intent = _infer_field_intent(field_hint)

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
        destination_hint = any(token in haystack for token in _DESTINATION_HINT_TOKENS)
        origin_hint = any(token in haystack for token in _ORIGIN_HINT_TOKENS)
        departure_date_hint = any(token in haystack for token in _DEPARTURE_DATE_HINT_TOKENS)
        return_date_hint = any(token in haystack for token in _RETURN_DATE_HINT_TOKENS)
        baggage_hint = any(token in haystack for token in _BAGGAGE_HINT_TOKENS)
        passenger_hint = any(token in haystack for token in _PASSENGER_HINT_TOKENS)
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

        if field_intent == "destination":
            if destination_hint:
                score += 20
            if origin_hint:
                score -= 24
        elif field_intent == "origin":
            if origin_hint:
                score += 20
            if destination_hint:
                score -= 16
        elif field_intent == "departure_date":
            if departure_date_hint:
                score += 16
            if return_date_hint:
                score -= 18
        elif field_intent == "return_date":
            if return_date_hint:
                score += 16
            if departure_date_hint:
                score -= 12
        elif field_intent == "baggage":
            if baggage_hint:
                score += 14
            if passenger_hint:
                score -= 10
        elif field_intent == "passengers":
            if passenger_hint:
                score += 14
            if baggage_hint:
                score -= 10

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
        if any(token in haystack for token in _DESTINATION_HINT_TOKENS):
            score += 8
        if any(token in haystack for token in _BAGGAGE_HINT_TOKENS):
            score += 6
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
    if any(unit in clean for unit in ("kg", "公斤", "lbs", "lb", "bag", "baggage", "luggage", "行李")):
        return "baggage"
    if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", clean):
        return "date"
    if re.fullmatch(r"[a-z]{3}", clean):
        return "airport"
    if re.search(r"\d", clean):
        return "numeric"
    return "text"


def _looks_like_date_literal(value_text: str) -> bool:
    clean = (value_text or "").strip().casefold()
    if not clean:
        return False
    return re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", clean) is not None


def _infer_field_intent(field_hint: Optional[str]) -> str:
    clean = (field_hint or "").strip().casefold()
    if not clean:
        return "generic"

    def has_any(tokens: set[str]) -> bool:
        return any(_contains_hint_token(clean, token) for token in tokens)

    if has_any(_DESTINATION_HINT_TOKENS):
        return "destination"
    if has_any(_ORIGIN_HINT_TOKENS):
        return "origin"
    if has_any(_RETURN_DATE_HINT_TOKENS):
        return "return_date"
    if has_any(_DEPARTURE_DATE_HINT_TOKENS):
        return "departure_date"
    if has_any(_BAGGAGE_HINT_TOKENS):
        return "baggage"
    if has_any(_PASSENGER_HINT_TOKENS):
        return "passengers"
    return "generic"


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
_DESTINATION_HINT_TOKENS = {"to", "destination", "arrive", "arrival", "where to", "到", "目的地", "到达"}
_ORIGIN_HINT_TOKENS = {"from", "origin", "depart", "departure", "where from", "出发", "始发"}
_BAGGAGE_HINT_TOKENS = {"bag", "baggage", "luggage", "carry-on", "checked", "kg", "lbs", "行李", "托运"}
_DATE_HINT_TOKENS = {"date", "day", "depart", "departure", "return", "日期", "时间", "出发"}
_DEPARTURE_DATE_HINT_TOKENS = {
    "date",
    "depart",
    "departure",
    "outbound",
    "check-in",
    "check in",
    "出发",
    "去程",
}
_RETURN_DATE_HINT_TOKENS = {
    "return",
    "inbound",
    "check-out",
    "check out",
    "返程",
    "回程",
    "退房",
}
_PASSENGER_HINT_TOKENS = {
    "passenger",
    "passengers",
    "traveler",
    "travellers",
    "pax",
    "adult",
    "adults",
    "guest",
    "guests",
    "乘客",
    "旅客",
    "人数",
}
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
