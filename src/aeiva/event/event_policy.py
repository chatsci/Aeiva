from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, List, Tuple

from aeiva.event.event_names import EventNames


@dataclass(frozen=True)
class EventPolicy:
    mode: str = "mutating"  # mutating | readonly
    consistency_scope: str = "session"  # session | user | global
    priority: int = 0


DEFAULT_EVENT_POLICY = EventPolicy()


def _compile_event_pattern(event_pattern: str) -> re.Pattern[str]:
    fragments = [re.escape(part) for part in event_pattern.split("*")]
    regex = ".*".join(fragments)
    return re.compile(rf"^{regex}$")


_POLICY_RULES: List[Tuple[str, EventPolicy]] = [
    (EventNames.ALL_RESPONSE, EventPolicy(mode="readonly", consistency_scope="global", priority=5)),
    (EventNames.COGNITION_QUERY, EventPolicy(mode="readonly", consistency_scope="session", priority=3)),
    (EventNames.COGNITION_QUERY_RESPONSE, EventPolicy(mode="readonly", consistency_scope="session", priority=3)),
    (EventNames.WORLD_QUERY, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.WORLD_QUERY_RESPONSE, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.MEMORY_QUERY, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.MEMORY_RETRIEVE, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.MEMORY_GET, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.MEMORY_FILTER, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.MEMORY_RETRIEVED, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.MEMORY_FILTERED, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.LIFERPG_QUERY, EventPolicy(mode="readonly", consistency_scope="session", priority=2)),
    (EventNames.COGNITION_THOUGHT, EventPolicy(mode="readonly", consistency_scope="session", priority=1)),
]

_COMPILED_RULES: List[Tuple[re.Pattern[str], EventPolicy]] = [
    (_compile_event_pattern(pattern), policy) for pattern, policy in _POLICY_RULES
]


def resolve_event_policy(event_name: str) -> EventPolicy:
    for pattern, policy in _COMPILED_RULES:
        if pattern.fullmatch(event_name):
            return policy
    return DEFAULT_EVENT_POLICY


EventPolicyResolver = Callable[[str], EventPolicy]
