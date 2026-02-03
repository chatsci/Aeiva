"""
MultiAgentSystem (MAS): orchestrate multiple Agent instances with event bridges.

Design goals:
- Agent is the unit of composition; MAS depends on agent/, not vice versa.
- Fully async, event-driven, minimal coupling.
- Safe forwarding with Signal lineage (hop_count increments).
"""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from aeiva.agent.agent import Agent
from aeiva.event.event import Event
from aeiva.event.event_names import EventNames
from aeiva.neuron import Signal

DEFAULT_MAIN_AGENT = "main"

ROLE_DEFAULT_MODULES: Dict[str, Dict[str, bool]] = {
    "main": {
        "perception": True,
        "cognition": True,
        "memory": False,
        "raw_memory": False,
        "raw_memory_summary": False,
        "emotion": False,
        "goal": False,
        "world_model": True,
        "action": True,
    },
    "memory": {
        "perception": False,
        "cognition": False,
        "memory": False,
        "raw_memory": True,
        "raw_memory_summary": True,
        "emotion": False,
        "goal": False,
        "world_model": False,
        "action": False,
    },
    "emotion": {
        "perception": False,
        "cognition": False,
        "memory": False,
        "raw_memory": False,
        "raw_memory_summary": False,
        "emotion": True,
        "goal": True,
        "world_model": False,
        "action": False,
    },
}

DEFAULT_LINKS = [
    {
        "source": "main",
        "target": "memory",
        "events": [
            EventNames.PERCEPTION_OUTPUT,
            EventNames.COGNITION_THOUGHT,
            EventNames.RAW_MEMORY_UTTERANCE,
            EventNames.RAW_MEMORY_USER_UPDATE,
        ],
    },
    {
        "source": "main",
        "target": "emotion",
        "events": [
            EventNames.PERCEPTION_OUTPUT,
            EventNames.COGNITION_THOUGHT,
            EventNames.ACTION_RESULT,
            EventNames.EMOTION_QUERY,
            EventNames.EMOTION_REGULATE,
            EventNames.EMOTION_UPDATE,
            EventNames.GOAL_UPDATE,
            EventNames.GOAL_QUERY,
        ],
    },
    {
        "source": "memory",
        "target": "main",
        "events": [
            EventNames.SUMMARY_MEMORY_RESULT,
            EventNames.RAW_MEMORY_RESULT,
            EventNames.RAW_MEMORY_ERROR,
        ],
    },
    {
        "source": "emotion",
        "target": "main",
        "events": [
            EventNames.EMOTION_CHANGED,
            EventNames.GOAL_CHANGED,
        ],
    },
]


@dataclass
class AgentSpec:
    name: str
    role: str = "custom"
    overrides: Dict[str, Any] = field(default_factory=dict)
    modules: Dict[str, bool] = field(default_factory=dict)
    llm_gateway_config: Optional[Dict[str, Any]] = None


@dataclass
class BridgeSpec:
    source: str
    target: str
    events: List[str]


class EventBridge:
    """Forward matching events from one agent to another."""

    def __init__(
        self,
        name: str,
        source: Agent,
        target: Agent,
        patterns: Iterable[str],
    ) -> None:
        self.name = name
        self.source = source
        self.target = target
        self.patterns = list(patterns)
        self._callbacks: List[Any] = []

    def bind(self) -> None:
        if not self.source.event_bus or not self.target.event_bus:
            return
        for pattern in self.patterns:
            async def _forward(event: Event, *, _pattern: str = pattern) -> None:
                await self.forward(event, _pattern)

            _forward.__name__ = f"mas_bridge_{self.name}_{pattern.replace('*', 'any').replace('.', '_')}"
            self.source.event_bus.subscribe(pattern, _forward)
            self._callbacks.append(_forward)

    def unbind(self) -> None:
        if not self.source.event_bus:
            return
        for callback in self._callbacks:
            self.source.event_bus.unsubscribe(callback)
        self._callbacks.clear()

    async def forward(self, event: Event, pattern: str) -> None:
        if not self.target.event_bus:
            return
        payload = event.payload
        if isinstance(payload, Signal):
            payload = payload.child(source=payload.source, data=payload.data)
        await self.target.event_bus.emit(event.name, payload=payload, priority=event.priority)


class MultiAgentSystem:
    """
    Multi-agent system composed of multiple Agent instances plus bridges.

    - Agents run independently on their own EventBus.
    - Bridges forward events between agents (event-driven coupling).
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mas_config = config.get("mas_config", {}) or {}
        self.main_agent_name = self.mas_config.get("main_agent", DEFAULT_MAIN_AGENT)
        self.agents: Dict[str, Agent] = {}
        self.bridges: List[EventBridge] = []
        self._stop_callbacks: List[Any] = []
        self._stop_requested = False

    @property
    def main_agent(self) -> Agent:
        return self.agents[self.main_agent_name]

    def request_stop(self) -> None:
        self._stop_requested = True
        for agent in self.agents.values():
            agent.request_stop()

    def setup(self) -> None:
        self._build_agents()
        for agent in self.agents.values():
            agent.setup()
        self._build_bridges()
        self._bind_stop_listeners()

    async def setup_async(self) -> None:
        self._build_agents()
        for agent in self.agents.values():
            await agent.setup_async()
        self._build_bridges()
        self._bind_stop_listeners()

    async def run(self, raw_memory_session: Optional[Dict[str, Any]] = None) -> None:
        tasks = []
        for name, agent in self.agents.items():
            if raw_memory_session and agent.raw_memory:
                session = raw_memory_session
            elif name == self.main_agent_name:
                session = raw_memory_session
            else:
                session = None
            tasks.append(asyncio.create_task(agent.run(raw_memory_session=session)))
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

    # ------------------------------------------------
    # Build helpers
    # ------------------------------------------------

    def _build_agents(self) -> None:
        specs = self._resolve_agent_specs()
        for spec in specs:
            agent_config = self._build_agent_config(spec)
            self.agents[spec.name] = Agent(agent_config)

    def _resolve_agent_specs(self) -> List[AgentSpec]:
        agents = self.mas_config.get("agents")
        if not agents:
            return [
                AgentSpec(name=DEFAULT_MAIN_AGENT, role="main"),
                AgentSpec(name="memory", role="memory"),
                AgentSpec(name="emotion", role="emotion"),
            ]
        specs: List[AgentSpec] = []
        if isinstance(agents, dict):
            for name, spec in agents.items():
                specs.append(self._spec_from_dict(name, spec))
        elif isinstance(agents, list):
            for spec in agents:
                if isinstance(spec, dict):
                    name = spec.get("name") or spec.get("id")
                    if not name:
                        continue
                    specs.append(self._spec_from_dict(name, spec))
        return specs

    def _spec_from_dict(self, name: str, data: Dict[str, Any]) -> AgentSpec:
        role = data.get("role", "custom")
        overrides = data.get("overrides") or data.get("config") or {}
        modules = data.get("modules") or {}
        llm_override = data.get("llm_gateway_config")
        return AgentSpec(
            name=name,
            role=role,
            overrides=dict(overrides),
            modules=dict(modules),
            llm_gateway_config=llm_override,
        )

    def _build_agent_config(self, spec: AgentSpec) -> Dict[str, Any]:
        cfg = copy.deepcopy(self.config)
        cfg = _deep_merge(cfg, spec.overrides)
        if spec.llm_gateway_config:
            cfg["llm_gateway_config"] = dict(spec.llm_gateway_config)

        modules = self._resolve_modules(spec)
        self._apply_module_flags(cfg, modules)
        agent_cfg = cfg.get("agent_config") or {}
        if "ui_enabled" not in agent_cfg:
            agent_cfg["ui_enabled"] = spec.name == self.main_agent_name
        if "emotion_log_enabled" not in agent_cfg:
            agent_cfg["emotion_log_enabled"] = spec.role == "emotion"
        cfg["agent_config"] = agent_cfg
        return cfg

    def _resolve_modules(self, spec: AgentSpec) -> Dict[str, bool]:
        if spec.modules:
            return spec.modules
        return ROLE_DEFAULT_MODULES.get(spec.role, {})

    def _apply_module_flags(self, cfg: Dict[str, Any], modules: Dict[str, bool]) -> None:
        for module, enabled in modules.items():
            key = _module_config_key(module)
            if not key:
                continue
            block = cfg.get(key)
            if not isinstance(block, dict):
                block = {} if block is None else {"value": block}
            block["enabled"] = bool(enabled)
            cfg[key] = block

    def _build_bridges(self) -> None:
        links = self.mas_config.get("links") or DEFAULT_LINKS
        for link in links:
            spec = BridgeSpec(
                source=link.get("source", ""),
                target=link.get("target", ""),
                events=list(link.get("events", [])),
            )
            if not spec.events:
                continue
            if spec.source not in self.agents or spec.target not in self.agents:
                continue
            bridge = EventBridge(
                name=f"{spec.source}_to_{spec.target}",
                source=self.agents[spec.source],
                target=self.agents[spec.target],
                patterns=spec.events,
            )
            bridge.bind()
            self.bridges.append(bridge)

    def _bind_stop_listeners(self) -> None:
        for name, agent in self.agents.items():
            if not agent.event_bus:
                continue

            async def _on_stop(event: Event, *, _name: str = name) -> None:
                self.request_stop()

            _on_stop.__name__ = f"mas_stop_from_{name}"
            agent.event_bus.subscribe(EventNames.AGENT_STOP, _on_stop)
            self._stop_callbacks.append(_on_stop)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _module_config_key(module: str) -> Optional[str]:
    mapping = {
        "perception": "perception_config",
        "cognition": "cognition_config",
        "memory": "memory_config",
        "raw_memory": "raw_memory_config",
        "raw_memory_summary": "raw_memory_summary_config",
        "emotion": "emotion_config",
        "goal": "goal_config",
        "world_model": "world_model_config",
        "action": "action_config",
    }
    return mapping.get(module)
