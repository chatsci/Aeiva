from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class HostEndpointConfig:
    url: str
    tools: List[str] = field(default_factory=list)
    token: Optional[str] = None
    timeout: float = 30.0


@dataclass
class HostConfig:
    enabled: bool = False
    hosts: Dict[str, HostEndpointConfig] = field(default_factory=dict)
    route: Dict[str, str] = field(default_factory=dict)
    default_host: Optional[str] = None
    timeout: float = 30.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostConfig":
        if not isinstance(data, dict):
            return cls()
        enabled = bool(data.get("enabled", False))
        timeout = float(data.get("timeout", 30.0))
        default_host = data.get("default_host") or None
        route = dict(data.get("route") or {})

        hosts: Dict[str, HostEndpointConfig] = {}
        raw_hosts = data.get("hosts") or {}
        if isinstance(raw_hosts, dict):
            for name, cfg in raw_hosts.items():
                if not isinstance(cfg, dict):
                    continue
                url = cfg.get("url")
                if not url:
                    continue
                tools = list(cfg.get("tools") or [])
                token = cfg.get("token")
                host_timeout = float(cfg.get("timeout", timeout))
                hosts[name] = HostEndpointConfig(
                    url=str(url),
                    tools=[str(t) for t in tools],
                    token=token,
                    timeout=host_timeout,
                )

        return cls(
            enabled=enabled,
            hosts=hosts,
            route=route,
            default_host=default_host,
            timeout=timeout,
        )
