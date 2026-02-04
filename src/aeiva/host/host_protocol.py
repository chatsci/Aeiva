from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class HostInvokeRequest:
    tool: str
    args: Dict[str, Any]
    request_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class HostInvokeResult:
    ok: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
