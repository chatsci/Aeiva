from __future__ import annotations

from aeiva.liferpg.schema import (
    LIFERPG_LEVELS,
    apply_merge_patch,
    default_liferpg_profile,
    normalize_profile,
)


def test_default_profile_contains_core_sections() -> None:
    profile = default_liferpg_profile()

    assert set(profile.keys()) >= {
        "user",
        "state",
        "roles",
        "inventory",
        "projects",
        "todos",
    }
    assert isinstance(profile["roles"], list)
    assert isinstance(profile["projects"], list)


def test_apply_merge_patch_updates_nested_and_removes_null_fields() -> None:
    current = {
        "user": {
            "bio": {"name": "Bang", "birth_date": "1993-07-18"},
            "identity": "researcher",
        },
        "state": {"context": "build"},
    }
    patch = {
        "user": {"identity": "researcher + builder"},
        "state": None,
    }

    updated = apply_merge_patch(current, patch)

    assert updated["user"]["identity"] == "researcher + builder"
    assert updated["user"]["bio"]["name"] == "Bang"
    assert "state" not in updated


def test_normalize_profile_clamps_role_levels_and_radar_levels() -> None:
    profile = {
        "user": {"bio": {"name": "Bang"}},
        "roles": [
            {
                "name": "Researcher",
                "description": "Works on research problems.",
                "level": "L9",
                "radar": {
                    "template": "researcher",
                    "dimensions": [
                        {"name": "Problem Framing", "level": "L0"},
                        {"name": "Method", "level": "L4"},
                    ],
                },
            }
        ],
        "inventory": {},
        "projects": [],
        "todos": {},
    }

    normalized = normalize_profile(profile)
    role = normalized["roles"][0]

    assert role["level"] == "L5"
    assert role["radar"]["dimensions"][0]["level"] == "L1"
    assert role["radar"]["dimensions"][1]["level"] == "L4"
    assert LIFERPG_LEVELS == ["L1", "L2", "L3", "L4", "L5"]
