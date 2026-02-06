from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set

from aeiva.tool.registry import ToolRegistry
from aeiva.host.command_policy import ShellCommandPolicy


class HostRunner:
    """Executes tool calls locally with an allowlist."""

    def __init__(
        self,
        allowed_tools: Optional[Iterable[str]] = None,
        command_policy: Optional[ShellCommandPolicy] = None,
    ) -> None:
        self._allowed: Optional[Set[str]] = (
            {t for t in allowed_tools} if allowed_tools is not None else None
        )
        self._command_policy = command_policy or ShellCommandPolicy()
        self._registry = ToolRegistry()
        self._registry.discover()

    def _is_allowed(self, tool_name: str) -> bool:
        if self._allowed is None:
            return True
        return tool_name in self._allowed

    async def execute(self, tool: str, args: Dict[str, Any]) -> Any:
        if not self._is_allowed(tool):
            raise PermissionError(f"Tool not allowed on host: {tool}")
        if tool == "shell":
            ok, reason = self._command_policy.check(args.get("command"))
            if not ok:
                raise PermissionError(reason)
        return await self._registry.execute(tool, **args)

    def execute_sync(self, tool: str, args: Dict[str, Any]) -> Any:
        if not self._is_allowed(tool):
            raise PermissionError(f"Tool not allowed on host: {tool}")
        if tool == "shell":
            ok, reason = self._command_policy.check(args.get("command"))
            if not ok:
                raise PermissionError(reason)
        return self._registry.execute_sync(tool, **args)
