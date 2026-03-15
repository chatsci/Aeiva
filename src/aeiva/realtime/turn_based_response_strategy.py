from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TurnBasedResponseStrategy:
    """
    Unified response behavior for turn-based realtime pipeline.

    Keep a single profile switch to avoid scattered boolean flags in runtime code.
    """

    name: str
    llm_stream: bool
    emit_progress_hints: bool


_DEFAULT_PROFILE = "responsive"

_PROFILES: dict[str, TurnBasedResponseStrategy] = {
    # Existing behavior baseline: non-streaming model response with progress hints.
    "stable": TurnBasedResponseStrategy(
        name="stable",
        llm_stream=False,
        emit_progress_hints=True,
    ),
    # Faster perceived latency: stream tokens when available, keep hints while waiting.
    "responsive": TurnBasedResponseStrategy(
        name="responsive",
        llm_stream=True,
        emit_progress_hints=True,
    ),
    # Lowest UI churn profile for constrained environments.
    "quiet": TurnBasedResponseStrategy(
        name="quiet",
        llm_stream=False,
        emit_progress_hints=False,
    ),
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def resolve_turn_based_response_strategy(config_dict: Mapping[str, Any]) -> TurnBasedResponseStrategy:
    realtime_cfg = _as_mapping(config_dict.get("realtime_config"))
    turn_based_cfg = _as_mapping(realtime_cfg.get("turn_based"))
    profile = str(turn_based_cfg.get("response_profile", _DEFAULT_PROFILE)).strip().lower()
    strategy = _PROFILES.get(profile)
    if strategy is None:
        strategy = _PROFILES[_DEFAULT_PROFILE]
    return strategy


def supported_turn_based_response_profiles() -> tuple[str, ...]:
    return tuple(sorted(_PROFILES.keys()))

