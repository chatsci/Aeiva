from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from aeiva.host.host_config import HostConfig, HostEndpointConfig


@dataclass
class HostEndpoint:
    name: str
    url: str
    tools: set[str]
    token: Optional[str]
    timeout: float

    def build_headers(self) -> Dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}


class HostRouter:
    """Routes tool execution to a configured host endpoint."""

    def __init__(self, config: HostConfig):
        self.config = config
        self._hosts: Dict[str, HostEndpoint] = {}
        for name, host_cfg in config.hosts.items():
            self._hosts[name] = HostEndpoint(
                name=name,
                url=host_cfg.url.rstrip("/"),
                tools=set(host_cfg.tools),
                token=host_cfg.token,
                timeout=host_cfg.timeout or config.timeout,
            )

    def is_enabled(self) -> bool:
        return self.config.enabled and bool(self._hosts)

    def _pick_host(self, tool: str) -> Optional[HostEndpoint]:
        if not self.is_enabled():
            return None

        if tool in self.config.route:
            host_id = self.config.route.get(tool)
            host = self._hosts.get(host_id)
            if host and (not host.tools or tool in host.tools):
                return host

        # Pick any host that declares the tool
        for host in self._hosts.values():
            if not host.tools or tool in host.tools:
                return host

        # Fallback to default host if provided
        if self.config.default_host:
            host = self._hosts.get(self.config.default_host)
            if host:
                return host
        return None

    async def execute(self, tool: str, args: Dict[str, Any]) -> Any:
        host = self._pick_host(tool)
        if host is None:
            return None
        payload = {"tool": tool, "args": args, "id": str(uuid.uuid4())}
        async with httpx.AsyncClient(timeout=host.timeout) as client:
            resp = await client.post(
                f"{host.url}/invoke",
                json=payload,
                headers=host.build_headers(),
            )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return data.get("result")
        raise RuntimeError(data.get("error") or "host execution failed")

    def execute_sync(self, tool: str, args: Dict[str, Any]) -> Any:
        host = self._pick_host(tool)
        if host is None:
            return None
        payload = {"tool": tool, "args": args, "id": str(uuid.uuid4())}
        with httpx.Client(timeout=host.timeout) as client:
            resp = client.post(
                f"{host.url}/invoke",
                json=payload,
                headers=host.build_headers(),
            )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return data.get("result")
        raise RuntimeError(data.get("error") or "host execution failed")


def configure_host_router(config_dict: Dict[str, Any]) -> Optional[HostRouter]:
    host_cfg = HostConfig.from_dict(config_dict.get("host_config") or {})
    if not host_cfg.enabled:
        return None
    router = HostRouter(host_cfg)
    if not router.is_enabled():
        return None
    return router
