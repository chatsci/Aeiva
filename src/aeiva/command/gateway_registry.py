from __future__ import annotations

import copy
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from aeiva.command.command_utils import build_runtime


DEFAULT_SHARED_GATEWAY_ID = "main"
DEFAULT_SCOPE = "shared"
DEFAULT_SESSION_SCOPE = "shared"


@dataclass
class GatewayContext:
    gateway_id: str
    config: Dict[str, Any]
    runtime: Any
    agent: Any

    def request_stop(self) -> None:
        self.runtime.request_stop()


class GatewayRegistry:
    def __init__(
        self,
        base_config: Dict[str, Any],
        *,
        runtime_builder: Callable[[Dict[str, Any]], Tuple[Any, Any]] = build_runtime,
    ) -> None:
        self.base_config = base_config
        self._runtime_builder = runtime_builder
        self._contexts: Dict[str, GatewayContext] = {}

        gateway_cfg = base_config.get("gateway_config") or {}
        self.shared_gateway_id = gateway_cfg.get("shared_gateway_id", DEFAULT_SHARED_GATEWAY_ID)
        self.default_scope = gateway_cfg.get("default_scope", DEFAULT_SCOPE)
        self.default_session_scope = gateway_cfg.get("default_session_scope", DEFAULT_SESSION_SCOPE)

    @property
    def contexts(self) -> Dict[str, GatewayContext]:
        return dict(self._contexts)

    def resolve_channel_config(self, channel_id: str) -> Dict[str, Any]:
        cfg = copy.deepcopy(self.base_config.get(f"{channel_id}_config") or {})
        cfg.setdefault("gateway_scope", self.default_scope)
        scope = cfg["gateway_scope"]
        if scope == "shared":
            cfg.setdefault("gateway_id", self.shared_gateway_id)
        else:
            cfg.setdefault("gateway_id", f"{channel_id}-dedicated")
        cfg.setdefault("session_scope", self.default_session_scope)
        cfg.setdefault("channel_id", channel_id)
        raw_cfg = self.base_config.get("raw_memory_config") or {}
        cfg.setdefault("memory_user_id", raw_cfg.get("user_id", "User"))
        return cfg

    def get_context(self, channel_id: str, channel_cfg: Dict[str, Any]) -> GatewayContext:
        scope = channel_cfg.get("gateway_scope", self.default_scope)
        gateway_id = channel_cfg.get("gateway_id")
        if not gateway_id:
            gateway_id = self.shared_gateway_id if scope == "shared" else f"{channel_id}-dedicated"
            channel_cfg["gateway_id"] = gateway_id

        if gateway_id in self._contexts:
            return self._contexts[gateway_id]

        config = self._build_context_config(gateway_id, scope)
        runtime, agent = self._runtime_builder(config)
        context = GatewayContext(
            gateway_id=gateway_id,
            config=config,
            runtime=runtime,
            agent=agent,
        )
        self._contexts[gateway_id] = context
        return context

    async def get_context_async(self, channel_id: str, channel_cfg: Dict[str, Any]) -> GatewayContext:
        scope = channel_cfg.get("gateway_scope", self.default_scope)
        gateway_id = channel_cfg.get("gateway_id")
        if not gateway_id:
            gateway_id = self.shared_gateway_id if scope == "shared" else f"{channel_id}-dedicated"
            channel_cfg["gateway_id"] = gateway_id

        if gateway_id in self._contexts:
            return self._contexts[gateway_id]

        config = self._build_context_config(gateway_id, scope)
        result = self._runtime_builder(config)
        if asyncio.iscoroutine(result):
            runtime, agent = await result
        else:
            runtime, agent = result
        context = GatewayContext(
            gateway_id=gateway_id,
            config=config,
            runtime=runtime,
            agent=agent,
        )
        self._contexts[gateway_id] = context
        return context

    def _build_context_config(self, gateway_id: str, scope: str) -> Dict[str, Any]:
        if scope == "shared":
            return self.base_config

        cfg = copy.deepcopy(self.base_config)
        cfg["raw_memory_config"] = self._patch_raw_memory_config(cfg, gateway_id)
        cfg["goal_config"] = self._patch_goal_config(cfg, gateway_id)
        cfg["agent_config"] = self._patch_agent_config(cfg, gateway_id)
        return cfg

    def _patch_raw_memory_config(self, cfg: Dict[str, Any], gateway_id: str) -> Dict[str, Any]:
        raw_cfg = dict(cfg.get("raw_memory_config") or {})
        base_dir = raw_cfg.get("base_dir", "storage/memory")
        if base_dir == "storage/memory":
            raw_cfg["base_dir"] = str(Path(base_dir) / gateway_id)
        return raw_cfg

    def _patch_goal_config(self, cfg: Dict[str, Any], gateway_id: str) -> Dict[str, Any]:
        goal_cfg = dict(cfg.get("goal_config") or {})
        base_dir = goal_cfg.get("base_dir", "storage/goal")
        if base_dir == "storage/goal":
            goal_cfg["base_dir"] = str(Path(base_dir) / gateway_id)
        return goal_cfg

    def _patch_agent_config(self, cfg: Dict[str, Any], gateway_id: str) -> Dict[str, Any]:
        agent_cfg = dict(cfg.get("agent_config") or {})
        default_path = "storage/emotion/AgentEmotion.md"
        if agent_cfg.get("emotion_log_path", default_path) == default_path:
            agent_cfg["emotion_log_path"] = str(
                Path("storage") / "emotion" / gateway_id / "AgentEmotion.md"
            )
        return agent_cfg
