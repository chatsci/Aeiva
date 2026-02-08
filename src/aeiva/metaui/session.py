from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .protocol import MetaUISpec


class MetaUIPhase(str, Enum):
    IDLE = "idle"
    RENDERING = "rendering"
    INTERACTIVE = "interactive"
    EXECUTING = "executing"
    RECOVERING = "recovering"
    ERROR = "error"


@dataclass
class MetaUISession:
    ui_id: str
    session_id: Optional[str]
    spec: MetaUISpec
    state: Dict[str, Any] = field(default_factory=dict)
    phase: MetaUIPhase = MetaUIPhase.IDLE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_error: Optional[str] = None
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ui_id": self.ui_id,
            "session_id": self.session_id,
            "phase": self.phase.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_error": self.last_error,
            "version": self.version,
            "title": self.spec.title,
        }

    def update_phase(self, phase: MetaUIPhase, error: Optional[str] = None) -> None:
        self.phase = phase
        self.updated_at = time.time()
        self.last_error = error

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = time.time()
