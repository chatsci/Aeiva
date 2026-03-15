from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping


LIFERPG_LEVELS = ["L1", "L2", "L3", "L4", "L5"]


def _coerce_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_level(value: Any, default: str = "L1") -> str:
    text = _coerce_text(value, default).upper()
    if text in LIFERPG_LEVELS:
        return text
    if text.startswith("L"):
        try:
            idx = int(text[1:])
            if idx <= 1:
                return "L1"
            if idx >= 5:
                return "L5"
            return f"L{idx}"
        except Exception:
            return default
    return default


def default_liferpg_profile() -> Dict[str, Any]:
    return {
        "user": {
            "bio": {
                "name": "",
                "birth_date": "",
                "primary_profession": "",
            },
            "identity": "",
            "commitments": "",
            "control": "",
            "character": "",
        },
        "state": {
            "condition": "",
            "context": "",
        },
        "roles": [],
        "inventory": {
            "role_bags": {},
        },
        "projects": [],
        "todos": {
            "year": [],
            "month": [],
            "week": [],
            "day": [],
        },
    }


def apply_merge_patch(current: Mapping[str, Any], patch: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Apply JSON Merge Patch (RFC 7396) semantics.

    - object values are merged recursively
    - null removes keys
    - scalar/list replaces value directly
    """
    base = copy.deepcopy(dict(current))
    for key, value in patch.items():
        if value is None:
            base.pop(key, None)
            continue
        if isinstance(value, Mapping) and isinstance(base.get(key), Mapping):
            base[key] = apply_merge_patch(dict(base.get(key) or {}), value)
            continue
        if isinstance(value, Mapping):
            base[key] = apply_merge_patch({}, value)
            continue
        base[key] = copy.deepcopy(value)
    return base


def _normalize_role(role: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = {
        "name": _coerce_text(role.get("name")),
        "description": _coerce_text(role.get("description")),
        "level": _normalize_level(role.get("level"), "L1"),
        "radar": {
            "template": _coerce_text((role.get("radar") or {}).get("template")),
            "dimensions": [],
        },
        "achievements": [],
    }

    radar = role.get("radar") if isinstance(role.get("radar"), Mapping) else {}
    dimensions = radar.get("dimensions") if isinstance(radar, Mapping) else []
    if isinstance(dimensions, list):
        for item in dimensions:
            if not isinstance(item, Mapping):
                continue
            name = _coerce_text(item.get("name"))
            if not name:
                continue
            normalized["radar"]["dimensions"].append(
                {
                    "name": name,
                    "level": _normalize_level(item.get("level"), "L1"),
                }
            )

    achievements = role.get("achievements")
    if isinstance(achievements, list):
        normalized["achievements"] = [
            _coerce_text(item)
            for item in achievements
            if _coerce_text(item)
        ]
    return normalized


def _normalize_projects(projects: Any) -> List[Dict[str, Any]]:
    if not isinstance(projects, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for project in projects:
        if not isinstance(project, Mapping):
            continue
        milestones = project.get("milestones") if isinstance(project.get("milestones"), list) else []
        normalized.append(
            {
                "title": _coerce_text(project.get("title")),
                "description": _coerce_text(project.get("description")),
                "milestones": [_coerce_text(m) for m in milestones if _coerce_text(m)],
                "deadline": _coerce_text(project.get("deadline")),
                "status": _coerce_text(project.get("status"), "active"),
            }
        )
    return normalized


def _normalize_todos(todos: Any) -> Dict[str, List[Dict[str, str]]]:
    result = {
        "year": [],
        "month": [],
        "week": [],
        "day": [],
    }
    if not isinstance(todos, Mapping):
        return result
    for bucket in result:
        items = todos.get(bucket)
        if not isinstance(items, list):
            continue
        normalized_items: List[Dict[str, str]] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            description = _coerce_text(item.get("description"))
            if not description:
                continue
            normalized_items.append(
                {
                    "description": description,
                    "deadline": _coerce_text(item.get("deadline")),
                    "status": _coerce_text(item.get("status"), "todo"),
                }
            )
        result[bucket] = normalized_items
    return result


def normalize_profile(profile: Mapping[str, Any]) -> Dict[str, Any]:
    base = default_liferpg_profile()
    data = dict(profile or {})

    user = data.get("user") if isinstance(data.get("user"), Mapping) else {}
    bio = user.get("bio") if isinstance(user.get("bio"), Mapping) else {}
    base["user"]["bio"]["name"] = _coerce_text(bio.get("name"))
    base["user"]["bio"]["birth_date"] = _coerce_text(bio.get("birth_date"))
    base["user"]["bio"]["primary_profession"] = _coerce_text(bio.get("primary_profession"))
    base["user"]["identity"] = _coerce_text(user.get("identity"))
    base["user"]["commitments"] = _coerce_text(user.get("commitments"))
    base["user"]["control"] = _coerce_text(user.get("control"))
    base["user"]["character"] = _coerce_text(user.get("character"))

    state = data.get("state") if isinstance(data.get("state"), Mapping) else {}
    base["state"]["condition"] = _coerce_text(state.get("condition"))
    base["state"]["context"] = _coerce_text(state.get("context"))

    roles = data.get("roles") if isinstance(data.get("roles"), list) else []
    base["roles"] = [_normalize_role(role) for role in roles if isinstance(role, Mapping)]

    inventory = data.get("inventory") if isinstance(data.get("inventory"), Mapping) else {}
    role_bags = inventory.get("role_bags") if isinstance(inventory.get("role_bags"), Mapping) else {}
    normalized_role_bags: Dict[str, List[str]] = {}
    for role_name, entries in role_bags.items():
        role_key = _coerce_text(role_name)
        if not role_key:
            continue
        if isinstance(entries, list):
            normalized_entries = [_coerce_text(item) for item in entries if _coerce_text(item)]
        else:
            normalized_entries = []
        normalized_role_bags[role_key] = normalized_entries
    base["inventory"]["role_bags"] = normalized_role_bags

    base["projects"] = _normalize_projects(data.get("projects"))
    base["todos"] = _normalize_todos(data.get("todos"))

    return base
