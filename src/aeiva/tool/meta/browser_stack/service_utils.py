"""Shared helper utilities for BrowserService orchestration."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, quote_plus, unquote_plus, urlsplit

from .browser_runtime import DEFAULT_TIMEOUT_MS
from .runtime_common import _normalize_timeout as _normalize_timeout_ms
from .value_utils import _as_bool, _as_int, _as_str, _coalesce


_SHORTHAND_RULES: tuple[tuple[set[str], str, str], ...] = (
    ({"to", "destination", "where_to"}, "to", "type_or_option"),
    ({"from", "origin", "where_from"}, "from", "type_or_option"),
    ({"date"}, "date", "set_date"),
    ({"sort", "order", "sort_by"}, "sort", "choose_option"),
    ({"query", "search", "search_query", "keyword", "keywords"}, "search query", "search_query"),
)


def _normalize_timeout(timeout: Optional[int]) -> int:
    return _normalize_timeout_ms(timeout, default=DEFAULT_TIMEOUT_MS)


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


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
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


def _looks_like_bot_challenge(payload: Dict[str, Any]) -> bool:
    if _looks_like_google_sorry(payload):
        return True
    url = (_as_str(payload.get("url")) or "").lower()
    title = (_as_str(payload.get("title")) or "").lower()
    strong_url_markers = (
        "/captcha",
        "recaptcha",
        "hcaptcha",
        "/challenge",
        "__cf_chl_",
        "/cdn-cgi/challenge",
        "/cdn-cgi/challenge-platform",
        "distil_r_captcha",
        "geo.captcha-delivery.com",
        "challenges.cloudflare.com",
    )
    strong_title_markers = (
        "captcha",
        "verify you are human",
        "are you human",
        "robot check",
        "security check",
    )
    weak_title_markers = (
        "attention required",
        "just a moment",
    )
    url_markers = (
        "__cf_chl_",
        "/cdn-cgi/",
        "challenge-platform",
        "challenges.cloudflare.com",
    )
    if any(marker in url for marker in strong_url_markers):
        return True
    if any(marker in title for marker in strong_title_markers):
        return True
    if any(marker in title for marker in weak_title_markers) and any(marker in url for marker in url_markers):
        return True
    return False


def _extract_search_query_from_url(url: Optional[str]) -> Optional[str]:
    clean = _as_str(url)
    if not clean:
        return None
    try:
        parsed = urlsplit(clean)
    except Exception:
        return None
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if not _is_search_results_url(host=host, path=path):
        return None
    parsed_params = _extract_search_params(parsed.query, parsed.fragment)
    for key in ("q", "query", "p", "wd", "text", "search_query", "search_term", "keyword", "k"):
        value = _first_non_empty_value(parsed_params, key)
        if value is not None:
            return value

    # Path-based search routes (e.g. /search/<query> or /results/<query>)
    segments = [seg for seg in path.split("/") if seg]
    for idx, seg in enumerate(segments):
        if seg in {"search", "results", "find"} and idx + 1 < len(segments):
            decoded = unquote_plus(segments[idx + 1]).strip()
            if decoded:
                return decoded
    return None


def _is_search_results_url(*, host: str, path: str) -> bool:
    if not host:
        return False
    if "google." in host and (path == "/search" or path.endswith("/search") or path == "/webhp"):
        return True
    if host.endswith("bing.com") and path.startswith("/search"):
        return True
    if "duckduckgo.com" in host and path in {"", "/"}:
        return True
    if "yahoo." in host and path.startswith("/search"):
        return True
    if host.endswith("baidu.com") and path.startswith("/s"):
        return True
    if host.endswith("yandex.com") and path.startswith("/search"):
        return True
    if host.endswith("ecosia.org") and path.startswith("/search"):
        return True
    return False


def _extract_search_params(query: str, fragment: str) -> Dict[str, list[str]]:
    merged: Dict[str, list[str]] = {}
    candidates = [query]
    if fragment and "=" in fragment:
        candidates.append(fragment.lstrip("#"))
    for raw in candidates:
        if not raw:
            continue
        try:
            parsed = parse_qs(raw, keep_blank_values=False)
        except Exception:
            continue
        for key, values in parsed.items():
            if key not in merged:
                merged[key] = list(values)
            else:
                merged[key].extend(values)
    return merged


def _first_non_empty_value(params: Dict[str, list[str]], key: str) -> Optional[str]:
    values = params.get(key)
    if not values:
        return None
    for value in values:
        clean = str(value).strip()
        if clean:
            return clean
    return None


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
    return [
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
