"""Structured logging helpers for browser-stack modules."""

from __future__ import annotations

import logging
from typing import Any, Mapping


def _normalize_log_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _render_log_kv(fields: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key, value in fields.items():
        if value is None:
            continue
        clean_key = str(key).strip()
        if not clean_key:
            continue
        parts.append(f"{clean_key}={_normalize_log_value(value)}")
    return " ".join(parts)


def _log_browser_event(
    logger: logging.Logger,
    *,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    payload = {"event": event}
    payload.update(fields)
    rendered = _render_log_kv(payload)
    logger.log(level, "browser %s", rendered)
