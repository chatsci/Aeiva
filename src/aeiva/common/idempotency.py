from __future__ import annotations

from collections import OrderedDict
import time
from typing import Any, Dict, Optional, Tuple


class IdempotencyCache:
    """Small in-memory TTL+LRU cache for idempotent request handling."""

    def __init__(self, *, max_entries: int = 4096, ttl_seconds: float = 600.0) -> None:
        self._max_entries = max(1, int(max_entries))
        self._ttl_seconds = max(1.0, float(ttl_seconds))
        self._items: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()

    def get(self, key: str) -> Tuple[bool, Any]:
        self._evict_expired()
        if key not in self._items:
            return False, None
        expires_at, value = self._items.pop(key)
        if expires_at <= time.monotonic():
            return False, None
        self._items[key] = (expires_at, value)
        return True, value

    def set(self, key: str, value: Any) -> None:
        self._evict_expired()
        if key in self._items:
            self._items.pop(key)
        while len(self._items) >= self._max_entries:
            self._items.popitem(last=False)
        self._items[key] = (time.monotonic() + self._ttl_seconds, value)

    def _evict_expired(self) -> None:
        now = time.monotonic()
        stale = [k for k, (expires_at, _value) in self._items.items() if expires_at <= now]
        for key in stale:
            self._items.pop(key, None)


def extract_signal_meta(signal: Any) -> Dict[str, Any]:
    if signal is None:
        return {}

    direct = getattr(signal, "meta", None)
    if isinstance(direct, dict) and direct:
        return direct

    data = getattr(signal, "data", None)
    if isinstance(data, dict):
        nested = data.get("meta") or data.get("metadata")
        if isinstance(nested, dict):
            return nested

    return {}


def extract_idempotency_key(signal: Any) -> Optional[str]:
    meta = extract_signal_meta(signal)
    raw_key = meta.get("idempotency_key")
    if not isinstance(raw_key, str):
        return None
    key = raw_key.strip()
    return key or None

