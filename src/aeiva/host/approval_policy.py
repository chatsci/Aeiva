from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Set


def _normalize(values: Optional[Iterable[str]]) -> Set[str]:
    if not values:
        return set()
    return {str(v).strip() for v in values if str(v).strip()}


@dataclass
class ApprovalPolicy:
    """
    Declarative approval policy for tool execution.

    - auto_approve: actions that never require confirmation
    - require_confirm: actions that always require confirmation
    """

    auto_approve: Set[str] = field(default_factory=set)
    require_confirm: Set[str] = field(default_factory=set)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ApprovalPolicy":
        if not isinstance(data, dict):
            return cls()
        return cls(
            auto_approve=_normalize(data.get("auto_approve")),
            require_confirm=_normalize(data.get("require_confirm")),
        )

    def classify(self, action_key: str) -> str:
        """
        Return: "auto", "confirm", or "default".
        """
        if action_key in self.require_confirm:
            return "confirm"
        if action_key in self.auto_approve:
            return "auto"
        return "default"
