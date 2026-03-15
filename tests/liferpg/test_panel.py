from __future__ import annotations

from aeiva.liferpg.panel import (
    _panel_header_html,
    build_liferpg_panel,
    build_panel_snapshot,
    get_dialogue_page_url,
    get_liferpg_page_url,
    is_liferpg_separate_page_enabled,
    render_radar_svg,
)


def test_render_radar_svg_outputs_svg_markup() -> None:
    svg = render_radar_svg(
        title="Researcher",
        dimensions=[("Problem Framing", "L4"), ("Method", "L3"), ("Writing", "L2")],
    )

    assert svg.strip().startswith("<svg")
    assert "polygon" in svg
    assert "Researcher" in svg


def test_build_panel_snapshot_contains_expected_sections() -> None:
    profile = {
        "user": {
            "bio": {
                "name": "Bang Liu",
                "birth_date": "1993-07-18",
                "primary_profession": "AI Engineer",
            },
            "identity": "Human-centered AI researcher and builder.",
            "commitments": "Human growth first.",
            "control": "Balanced delegation.",
            "character": "Direct, rigorous.",
        },
        "state": {
            "condition": "Energy medium, stress medium.",
            "context": "Building LifeRPG module.",
        },
        "roles": [
            {
                "name": "Researcher",
                "description": "Research role",
                "level": "L3",
                "radar": {
                    "template": "researcher",
                    "dimensions": [
                        {"name": "Problem Framing", "level": "L4"},
                        {"name": "Method", "level": "L3"},
                        {"name": "Writing", "level": "L2"},
                    ],
                },
                "achievements": ["2026-03-01 - Shipped schema v1"],
            }
        ],
        "inventory": {
            "role_bags": {
                "researcher": ["Draft paper: Human-Centered Agent"]
            }
        },
        "projects": [
            {
                "title": "LifeRPG Integration",
                "description": "Integrate module into Aeiva",
                "milestones": ["schema", "neuron", "panel"],
                "deadline": "2026-04-01",
                "status": "active",
            }
        ],
        "todos": {
            "day": [{"description": "finish tests", "deadline": "2026-03-14", "status": "doing"}],
            "week": [],
            "month": [],
            "year": [],
        },
    }
    templates = {
        "researcher": {
            "display_name": "Researcher",
            "dimensions": ["Problem Framing", "Method", "Writing"],
        }
    }

    snapshot = build_panel_snapshot(profile, templates)

    assert "Bang Liu" in snapshot.overview_markdown
    assert len(snapshot.role_cards) == 1
    assert "LifeRPG Integration" in snapshot.projects_markdown
    assert "finish tests" in snapshot.todos_markdown


def test_separate_page_flag_is_read_from_panel_config() -> None:
    cfg = {"liferpg_config": {"enabled": True, "panel": {"separate_page": True}}}

    assert is_liferpg_separate_page_enabled(cfg) is True


def test_get_liferpg_page_url_uses_panel_server_settings() -> None:
    cfg = {
        "liferpg_config": {
            "enabled": True,
            "panel": {
                "separate_page": True,
                "server_name": "127.0.0.1",
                "server_port": 7862,
            },
        }
    }

    assert get_liferpg_page_url(cfg) == "http://127.0.0.1:7862"


def test_get_dialogue_page_url_prefers_realtime_server_settings() -> None:
    cfg = {
        "realtime_config": {
            "enabled": True,
            "server_name": "127.0.0.1",
            "server_port": 7860,
        }
    }

    assert get_dialogue_page_url(cfg) == "http://127.0.0.1:7860"


def test_build_liferpg_panel_skips_embed_when_separate_page_enabled() -> None:
    cfg = {"liferpg_config": {"enabled": True, "panel": {"separate_page": True}}}

    assert build_liferpg_panel(gr=object(), config_dict=cfg) is None


def test_panel_header_exposes_navigation_links_for_standalone_dashboard() -> None:
    profile = {
        "user": {
            "bio": {
                "name": "Bang Liu",
                "birth_date": "1993-07-18",
                "primary_profession": "AI Engineer",
            },
            "identity": "Human-centered AI researcher and builder.",
        },
        "state": {
            "condition": "Energy medium, stress medium.",
            "context": "Building LifeRPG module.",
        },
        "roles": [{"name": "Researcher"}],
        "projects": [{"title": "LifeRPG Integration"}],
        "inventory": {"role_bags": {"researcher": ["Paper Draft"]}},
        "todos": {"day": [{"description": "finish tests"}], "week": [], "month": [], "year": []},
    }

    header_html = _panel_header_html(
        profile,
        style_name="minimal",
        icon_pack="default",
        dialogue_url="http://127.0.0.1:7860",
    )

    assert "#roles" in header_html
    assert "#projects" in header_html
    assert "Open Dialogue" in header_html
