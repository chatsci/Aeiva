from __future__ import annotations

from aeiva.liferpg.storage import LifeRPGStore, default_radar_templates


def test_store_ensure_initialized_creates_profile_and_templates(tmp_path) -> None:
    store = LifeRPGStore(
        base_dir=str(tmp_path),
        profile_filename="liferpg.yaml",
        templates_filename="radar_templates.yaml",
    )

    store.ensure_initialized()

    assert store.profile_path.exists()
    assert store.templates_path.exists()

    profile = store.read_profile()
    templates = store.read_templates()
    assert isinstance(profile, dict)
    assert isinstance(templates, dict)
    assert "researcher" in templates


def test_store_write_profile_roundtrip(tmp_path) -> None:
    store = LifeRPGStore(base_dir=str(tmp_path))
    store.ensure_initialized()

    profile = store.read_profile()
    profile["user"]["bio"]["name"] = "Bang Liu"
    profile["projects"] = [
        {
            "title": "Build Aeiva",
            "description": "Implement local-first agent stack",
            "milestones": ["liferpg module"],
            "deadline": "2026-06-30",
            "status": "active",
        }
    ]

    store.write_profile(profile)
    reloaded = store.read_profile()

    assert reloaded["user"]["bio"]["name"] == "Bang Liu"
    assert reloaded["projects"][0]["title"] == "Build Aeiva"


def test_default_templates_have_level_schema() -> None:
    templates = default_radar_templates()

    assert "_level_schema" in templates
    assert templates["_level_schema"]["levels"] == ["L1", "L2", "L3", "L4", "L5"]
