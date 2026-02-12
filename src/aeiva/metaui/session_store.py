from __future__ import annotations

from copy import deepcopy
from typing import Dict, Mapping, Optional

from .session import MetaUISession


def phase_counts(sessions: Mapping[str, MetaUISession]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for session in sessions.values():
        phase_name = session.phase.value
        counts[phase_name] = counts.get(phase_name, 0) + 1
    return counts


def list_sessions_sorted(sessions: Mapping[str, MetaUISession]) -> list[dict]:
    items = [session.to_dict() for session in sessions.values()]
    items.sort(key=lambda item: item["updated_at"], reverse=True)
    return items


def snapshot_session(
    sessions: Mapping[str, MetaUISession],
    *,
    ui_id: str,
) -> Optional[Dict[str, object]]:
    session = sessions.get(ui_id)
    if session is None:
        return None
    snapshot = session.to_dict()
    snapshot["state"] = deepcopy(session.state)
    return {
        "session": snapshot,
        "spec": session.spec.model_dump(mode="json"),
    }

