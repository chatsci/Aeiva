"""Shared helper utilities for BrowserService orchestration."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from .runtime import DEFAULT_TIMEOUT_MS


_SHORTHAND_RULES: tuple[tuple[set[str], str, str], ...] = (
    ({"to", "destination", "arrive", "arrival", "where_to"}, "to", "type_or_option"),
    ({"from", "origin", "depart", "departure", "where_from"}, "from", "type_or_option"),
    ({"date", "departure_date", "depart_date", "outbound_date"}, "departure date", "set_date"),
    ({"check_in", "checkin", "check_in_date", "checkin_date"}, "check-in date", "set_date"),
    (
        {"check_out", "checkout", "check_out_date", "checkout_date", "return_date", "inbound_date"},
        "check-out date",
        "set_date",
    ),
    ({"baggage", "bag", "checked_baggage", "checked_bag", "luggage"}, "checked baggage", "set_number"),
    ({"passengers", "passenger", "pax", "travellers", "travelers", "people"}, "passengers", "set_number"),
    ({"guests", "guest", "guest_count", "adults", "children"}, "guests", "set_number"),
    ({"cabin", "class", "seat_class", "travel_class"}, "cabin", "choose_option"),
    ({"trip_type", "trip", "journey_type"}, "trip type", "choose_option"),
    ({"sort", "order", "sort_by"}, "sort", "choose_option"),
    ({"query", "search", "search_query", "keyword", "keywords"}, "search query", "search_query"),
)


def _normalize_timeout(timeout: Optional[int]) -> int:
    if timeout is None:
        return DEFAULT_TIMEOUT_MS
    try:
        value = int(timeout)
    except Exception:
        return DEFAULT_TIMEOUT_MS
    return max(1, value)


def _extract_operation_name(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    return (
        _as_str(payload.get("operation"))
        or _as_str(payload.get("kind"))
        or _as_str(payload.get("action"))
        or _as_str(payload.get("op"))
        or ""
    ).lower()


def _expand_fill_fields_shorthand(
    *,
    fields: Dict[str, Any],
    submit: bool,
    confirm_date: bool = False,
) -> list[Dict[str, Any]]:
    steps: list[Dict[str, Any]] = []
    for raw_key, raw_value in fields.items():
        key = str(raw_key or "").strip().lower()
        if not key:
            continue
        normalized_key = key.replace("-", "_").replace(" ", "_")
        values = _try_normalize_values(raw_value)
        value = _as_str(raw_value) if values is None else None
        if value is None and not values:
            continue

        matched = _match_shorthand_rule(normalized_key)
        if matched is not None:
            _, field_name, mode = matched
            _append_shorthand_step(
                steps=steps,
                mode=mode,
                field_name=field_name,
                value=value,
                values=values,
                confirm_date=confirm_date,
            )
            continue

        if values:
            steps.append({"operation": "choose_option", "field": normalized_key, "values": values})
        else:
            steps.append({"operation": "type", "field": normalized_key, "value": value})

    if submit:
        steps.append({"operation": "submit"})
    return steps


def _match_shorthand_rule(normalized_key: str) -> Optional[tuple[set[str], str, str]]:
    for rule in _SHORTHAND_RULES:
        keys, _, _ = rule
        if normalized_key in keys:
            return rule
    return None


def _try_normalize_values(raw_value: Any) -> Optional[list[str]]:
    if not isinstance(raw_value, (list, tuple)):
        return None
    try:
        return _normalize_values(raw_value)
    except Exception:
        return None


def _append_shorthand_step(
    *,
    steps: list[Dict[str, Any]],
    mode: str,
    field_name: str,
    value: Optional[str],
    values: Optional[list[str]],
    confirm_date: bool,
) -> None:
    if mode == "type_or_option":
        if values:
            steps.append({"operation": "choose_option", "field": field_name, "values": values})
        else:
            steps.append({"operation": "type", "field": field_name, "value": value})
        return
    if mode == "set_date":
        step_value = values[0] if values else value
        step: Dict[str, Any] = {
            "operation": "set_date",
            "field": field_name,
            "value": step_value,
        }
        if confirm_date:
            step["confirm"] = True
        steps.append(step)
        return
    if mode == "set_number":
        step_value = values[0] if values else value
        steps.append({"operation": "set_number", "field": field_name, "value": step_value})
        return
    if mode == "choose_option":
        if values:
            steps.append({"operation": "choose_option", "field": field_name, "values": values})
        else:
            steps.append({"operation": "choose_option", "field": field_name, "value": value})
        return
    if mode == "search_query":
        step_value = values[0] if values else value
        steps.append({"operation": "type", "field": field_name, "value": step_value})
        return
    raise ValueError(f"unsupported shorthand mode: {mode}")


def _build_fill_fields_field_key(step: Dict[str, Any]) -> Optional[str]:
    field = (
        _as_str(step.get("field"))
        or _as_str(step.get("label"))
        or _as_str(step.get("name"))
    )
    if field:
        return field.casefold()
    return None


def _build_fill_fields_step_signature(*, step: Dict[str, Any], operation: str) -> tuple[Any, ...]:
    values = _fill_fields_signature_values(step)
    paths = _fill_fields_signature_paths(step)
    wait_time = _coalesce(
        _as_int(step.get("time_ms")),
        _as_int(step.get("timeMs")),
        _as_int(step.get("time")),
        0,
    )
    delta_x = _coalesce(_as_int(step.get("delta_x")), _as_int(step.get("deltaX")), 0)
    delta_y = _coalesce(_as_int(step.get("delta_y")), _as_int(step.get("deltaY")), 0)
    return (
        operation,
        _build_fill_fields_field_key(step) or "",
        _as_str(step.get("value")) or _as_str(step.get("text")) or "",
        _as_str(step.get("query")) or "",
        values,
        paths,
        _as_int(step.get("limit")) or 0,
        _as_str(step.get("selector")) or "",
        _as_str(step.get("ref")) or "",
        _as_bool(step.get("confirm"), default=False),
        _as_bool(step.get("double_click"), default=False)
        or _as_bool(step.get("doubleClick"), default=False),
        _as_str(step.get("button")) or "",
        _as_str(step.get("url")) or "",
        _as_str(step.get("key")) or "",
        _as_str(step.get("start_selector")) or _as_str(step.get("startSelector")) or "",
        _as_str(step.get("start_ref")) or _as_str(step.get("startRef")) or "",
        _as_str(step.get("end_selector")) or _as_str(step.get("endSelector")) or "",
        _as_str(step.get("end_ref")) or _as_str(step.get("endRef")) or "",
        _as_str(step.get("state"))
        or _as_str(step.get("selector_state"))
        or _as_str(step.get("selectorState"))
        or "",
        _as_str(step.get("text_gone")) or _as_str(step.get("textGone")) or "",
        _as_str(step.get("url_contains")) or _as_str(step.get("urlContains")) or "",
        wait_time,
        delta_x,
        delta_y,
    )


def _fill_fields_signature_values(step: Dict[str, Any]) -> tuple[str, ...]:
    raw_values = step.get("values")
    if raw_values is None and isinstance(step.get("value"), (list, tuple)):
        raw_values = step.get("value")
    if raw_values is None:
        return ()
    if isinstance(raw_values, (list, tuple)):
        items = [str(item).strip() for item in raw_values if str(item).strip()]
        return tuple(items)
    text = str(raw_values).strip()
    return (text,) if text else ()


def _fill_fields_signature_paths(step: Dict[str, Any]) -> tuple[str, ...]:
    raw_paths = step.get("paths")
    if raw_paths is None:
        return ()
    if isinstance(raw_paths, (list, tuple)):
        items = [str(item).strip() for item in raw_paths if str(item).strip()]
        return tuple(items)
    text = str(raw_paths).strip()
    return (text,) if text else ()


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _normalize_values(value: Any) -> list[str]:
    if value is None:
        raise ValueError("values are required for select operation")
    if isinstance(value, (list, tuple)):
        items = [str(v) for v in value if str(v).strip()]
        if items:
            return items
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    raise ValueError("values are required for select operation")


def _normalize_paths(value: Any) -> list[str]:
    if value is None:
        raise ValueError("paths are required for upload operation")
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, (list, tuple)):
        paths = [str(v).strip() for v in value if str(v).strip()]
        if paths:
            return paths
    raise ValueError("paths are required for upload operation")


def _classify_launch_failure(message: str) -> Optional[Dict[str, Any]]:
    text = (message or "").strip()
    if not text:
        return None

    lowered = text.lower()
    if (
        "playwright" not in lowered
        and "browsertype.launch" not in lowered
        and "failed to launch browser automation" not in lowered
        and "mach_port_rendezvous" not in lowered
        and "subprocess support is unavailable" not in lowered
        and "get_child_watcher" not in lowered
    ):
        return None

    details: Dict[str, Any] = {"category": "launch_failure"}
    if "subprocess support is unavailable" in lowered or "get_child_watcher" in lowered:
        details["category"] = "event_loop_policy"
        details["hint"] = (
            "The runtime event-loop policy does not support subprocess launch for the "
            "active loop. Restart Aeiva and avoid loop-policy overrides (e.g. uvloop) "
            "for the gateway loop."
        )
        return details

    if "mach_port_rendezvous" in lowered or "permission denied (1100)" in lowered:
        details["category"] = "sandbox_permission"
        details["hint"] = (
            "Browser launch was blocked by macOS sandbox permissions. "
            "Run Aeiva outside the sandboxed environment, or route browser execution "
            "to an unsandboxed host bridge."
        )
        return details

    if "executable doesn't exist" in lowered or "executable not found" in lowered:
        details["category"] = "browser_missing"
        details["hint"] = "Install browser binaries: playwright install chromium"
        return details

    if "playwright is not installed" in lowered:
        details["category"] = "dependency_missing"
        details["hint"] = "Install tool extras: pip install -e '.[tools]'"
        return details

    return details


def _looks_like_google_sorry(payload: Dict[str, Any]) -> bool:
    url = _as_str(payload.get("url")) or ""
    title = (_as_str(payload.get("title")) or "").lower()
    lowered_url = url.lower()
    if "google.com/sorry" in lowered_url:
        return True
    if "/sorry/" in lowered_url and "google." in lowered_url:
        return True
    if "unusual traffic" in title:
        return True
    return False


def _extract_scroll_y(value: Any) -> int:
    if isinstance(value, dict):
        return int(_as_int(value.get("y")) or 0)
    return 0


def _extract_container_scroll_y(value: Any, *, key: str) -> Optional[int]:
    if not isinstance(value, dict):
        return None
    nested = value.get(key)
    if isinstance(nested, dict):
        top = _as_int(nested.get("top"))
        if top is not None:
            return int(top)
    top = _as_int(value.get("top"))
    if top is not None:
        return int(top)
    return None


def _resolve_scroll_positions(payload: Dict[str, Any]) -> tuple[int, int, str]:
    active_container = payload.get("active_container_scroll")
    active_before = _extract_container_scroll_y(active_container, key="before")
    active_after = _extract_container_scroll_y(active_container, key="after")
    if active_before is not None or active_after is not None:
        return (
            int(active_before or active_after or 0),
            int(active_after or active_before or 0),
            "active_container",
        )

    container = payload.get("container_scroll")
    container_before = _extract_container_scroll_y(container, key="before")
    container_after = _extract_container_scroll_y(container, key="after")
    if container_before is not None or container_after is not None:
        return (
            int(container_before or container_after or 0),
            int(container_after or container_before or 0),
            "container",
        )

    before = payload.get("viewport_scroll_before")
    after = payload.get("viewport_scroll_after")
    return _extract_scroll_y(before), _extract_scroll_y(after), "viewport"


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _build_search_fallback_results(query: str) -> list[Dict[str, str]]:
    clean = (query or "").strip()
    encoded = quote_plus(clean)
    results: list[Dict[str, str]] = [
        {
            "title": f"Google Search: {clean}",
            "url": f"https://www.google.com/search?q={encoded}",
            "source": "fallback",
        },
        {
            "title": f"Bing Search: {clean}",
            "url": f"https://www.bing.com/search?q={encoded}",
            "source": "fallback",
        },
        {
            "title": f"DuckDuckGo Search: {clean}",
            "url": f"https://duckduckgo.com/?q={encoded}",
            "source": "fallback",
        },
    ]
    lower = clean.lower()
    if any(token in lower for token in ("flight", "airfare", "ticket", "机票", "航班")):
        results.extend(
            [
                {
                    "title": f"Google Flights: {clean}",
                    "url": f"https://www.google.com/travel/flights?q={encoded}",
                    "source": "fallback",
                },
                {
                    "title": f"Kayak Flights: {clean}",
                    "url": f"https://www.kayak.com/flights/{encoded}?sort=bestflight_a",
                    "source": "fallback",
                },
                {
                    "title": f"Skyscanner: {clean}",
                    "url": f"https://www.skyscanner.com/transport/flights/?q={encoded}",
                    "source": "fallback",
                },
                {
                    "title": f"Trip.com Flights: {clean}",
                    "url": f"https://www.trip.com/flights/?locale=en-US&curr=USD&searchword={encoded}",
                    "source": "fallback",
                },
            ]
        )
    return results


def _looks_like_flight_query(query: str) -> bool:
    lower = (query or "").strip().lower()
    if not lower:
        return False
    return any(token in lower for token in ("flight", "airfare", "ticket", "机票", "航班"))


def _build_flight_comparison_links(query: str) -> list[Dict[str, str]]:
    clean = (query or "").strip()
    if not clean:
        return []
    encoded = quote_plus(clean)
    return [
        {
            "source": "google_flights",
            "title": "Google Flights",
            "url": f"https://www.google.com/travel/flights?q={encoded}",
        },
        {
            "source": "kayak",
            "title": "Kayak",
            "url": f"https://www.kayak.com/flights/{encoded}?sort=bestflight_a",
        },
        {
            "source": "skyscanner",
            "title": "Skyscanner",
            "url": f"https://www.skyscanner.com/transport/flights/?q={encoded}",
        },
        {
            "source": "trip",
            "title": "Trip.com",
            "url": f"https://www.trip.com/flights/?locale=en-US&curr=USD&searchword={encoded}",
        },
    ]




