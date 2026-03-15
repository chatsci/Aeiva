from __future__ import annotations

import html
import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from aeiva.liferpg.storage import LifeRPGStore


logger = logging.getLogger(__name__)

_LEVEL_TO_VALUE = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
_LIFERPG_CSS = """
body {
  background:
    radial-gradient(circle at top left, rgba(244, 234, 216, 0.9) 0%, rgba(244, 234, 216, 0) 34%),
    linear-gradient(180deg, #f7f1e7 0%, #edf2ee 100%);
}
.gradio-container {
  max-width: 1420px !important;
  margin: 0 auto;
  padding: 26px 18px 56px !important;
}
.liferpg-shell {
  max-width: 1320px;
  margin: 0 auto;
  font-family: "Avenir Next", "Segoe UI", sans-serif;
  color: #1d2733;
}
.liferpg-shell * {
  box-sizing: border-box;
}
.liferpg-section {
  scroll-margin-top: 24px;
}
.liferpg-section + .liferpg-section {
  margin-top: 18px;
}
.liferpg-eyebrow {
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6d7a86;
  margin-bottom: 10px;
}
.liferpg-section-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}
.liferpg-page-title {
  margin: 0;
  font-family: "Iowan Old Style", "Palatino Linotype", serif;
  font-size: 2.7rem;
  line-height: 1.05;
  color: #16202a;
}
.liferpg-page-subtitle {
  margin: 12px 0 0;
  font-size: 1rem;
  line-height: 1.7;
  color: #4f5f6f;
}
.liferpg-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.liferpg-masthead,
.liferpg-hero,
.liferpg-grid-2,
.liferpg-role-grid,
.liferpg-todo-grid {
  display: grid;
  gap: 18px;
}
.liferpg-masthead {
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.9fr);
  align-items: stretch;
}
.liferpg-hero {
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 1fr);
}
.liferpg-grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.liferpg-role-grid {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}
.liferpg-todo-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.liferpg-card {
  background: linear-gradient(180deg, rgba(253, 250, 244, 0.98), rgba(246, 241, 232, 0.97));
  border: 1px solid rgba(179, 158, 127, 0.35);
  border-radius: 26px;
  box-shadow: 0 18px 44px rgba(38, 52, 62, 0.09);
  padding: 24px;
}
.liferpg-card-alt {
  background: linear-gradient(180deg, rgba(236, 244, 239, 0.98), rgba(228, 237, 231, 0.98));
}
.liferpg-masthead-card {
  background:
    radial-gradient(circle at top right, rgba(227, 235, 222, 0.7), rgba(227, 235, 222, 0) 36%),
    linear-gradient(180deg, rgba(252, 248, 241, 0.99), rgba(244, 239, 229, 0.97));
}
.liferpg-sidebar-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.liferpg-section-title {
  margin: 0 0 14px;
  font-family: "Iowan Old Style", "Palatino Linotype", serif;
  font-size: 1.42rem;
  color: #16202a;
}
.liferpg-section-subtitle {
  margin: 0;
  color: #5c6a77;
  line-height: 1.7;
}
.liferpg-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 14px;
}
.liferpg-field-label {
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6d7a86;
}
.liferpg-field-value {
  margin: 0;
  color: #24313d;
  line-height: 1.75;
}
.liferpg-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}
.liferpg-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 999px;
  background: rgba(18, 90, 84, 0.08);
  border: 1px solid rgba(18, 90, 84, 0.12);
  color: #134f48;
  font-size: 0.92rem;
}
.liferpg-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 20px;
}
.liferpg-nav-link,
.liferpg-nav-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 10px 14px;
  border-radius: 999px;
  text-decoration: none;
  font-size: 0.95rem;
  transition: transform 120ms ease, box-shadow 120ms ease;
}
.liferpg-nav-link {
  color: #184a43;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(24, 74, 67, 0.14);
}
.liferpg-nav-primary {
  color: #f8f5ef;
  background: linear-gradient(180deg, #17463f, #0f3530);
  border: 1px solid rgba(15, 53, 48, 0.32);
  box-shadow: 0 10px 24px rgba(15, 53, 48, 0.16);
}
.liferpg-nav-link:hover,
.liferpg-nav-primary:hover {
  transform: translateY(-1px);
}
.liferpg-kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 22px;
}
.liferpg-kpi {
  padding: 14px;
  border-radius: 16px;
  background: rgba(14, 79, 73, 0.07);
  border: 1px solid rgba(14, 79, 73, 0.11);
}
.liferpg-kpi-label {
  display: block;
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5f6e7b;
}
.liferpg-kpi-value {
  display: block;
  margin-top: 8px;
  font-size: 1.45rem;
  font-weight: 700;
  color: #16352f;
}
.liferpg-role-card svg {
  width: 100%;
  height: auto;
  margin-top: 10px;
}
.liferpg-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.liferpg-meta-tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(201, 144, 78, 0.14);
  border: 1px solid rgba(201, 144, 78, 0.2);
  color: #8a5521;
  font-size: 0.84rem;
}
.liferpg-list {
  list-style: none;
  margin: 14px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.liferpg-list li {
  margin: 0;
  padding: 11px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.64);
  border: 1px solid rgba(29, 39, 51, 0.08);
  line-height: 1.55;
}
.liferpg-muted {
  color: #667788;
}
.liferpg-route-note {
  margin-top: 14px;
  color: #556370;
  line-height: 1.6;
}
.liferpg-project-card,
.liferpg-bag-card {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(29, 39, 51, 0.08);
}
.liferpg-project-title,
.liferpg-bag-title,
.liferpg-todo-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #182430;
}
.liferpg-project-body,
.liferpg-bag-body {
  margin: 8px 0 0;
  color: #495867;
  line-height: 1.65;
}
.liferpg-todo-column {
  min-height: 100%;
}
@media (max-width: 1100px) {
  .liferpg-masthead,
  .liferpg-hero,
  .liferpg-grid-2,
  .liferpg-todo-grid {
    grid-template-columns: 1fr;
  }
  .liferpg-kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .liferpg-page-title {
    font-size: 2.1rem;
  }
  .liferpg-card {
    padding: 18px;
  }
  .liferpg-kpi-row {
    grid-template-columns: 1fr;
  }
  .liferpg-nav {
    flex-direction: column;
  }
  .liferpg-nav-link,
  .liferpg-nav-primary {
    width: 100%;
  }
}
"""


@dataclass(frozen=True)
class RoleCard:
    name: str
    level: str
    description: str
    radar_svg: str
    achievements_markdown: str


@dataclass(frozen=True)
class PanelSnapshot:
    overview_markdown: str
    role_cards: List[RoleCard]
    inventory_markdown: str
    projects_markdown: str
    todos_markdown: str


@dataclass(frozen=True)
class LifeRPGPanelComponents:
    refresh_fn: Callable[[], Tuple[str, str, str, str, str, str]]
    outputs: List[Any]


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _level_to_value(level: str) -> int:
    return _LEVEL_TO_VALUE.get(str(level).strip().upper(), 1)


def render_radar_svg(
    *,
    title: str,
    dimensions: Sequence[Tuple[str, str]],
    size: int = 280,
) -> str:
    if not dimensions:
        dimensions = [("N/A", "L1")]

    radius = size * 0.32
    cx = size / 2
    cy = size / 2 + 8
    total = len(dimensions)

    def _point(idx: int, value: float) -> Tuple[float, float]:
        angle = (2 * math.pi * idx / total) - (math.pi / 2)
        x = cx + math.cos(angle) * radius * value
        y = cy + math.sin(angle) * radius * value
        return x, y

    rings: List[str] = []
    for step in range(1, 6):
        factor = step / 5.0
        ring_points = [_point(i, factor) for i in range(total)]
        ring_path = " ".join(f"{x:.2f},{y:.2f}" for x, y in ring_points)
        rings.append(
            f"<polygon points='{ring_path}' fill='none' stroke='#e5e7eb' stroke-width='1' />"
        )

    axis_lines: List[str] = []
    labels: List[str] = []
    shape_points: List[str] = []
    for idx, (name, level) in enumerate(dimensions):
        x, y = _point(idx, 1.0)
        axis_lines.append(
            f"<line x1='{cx:.2f}' y1='{cy:.2f}' x2='{x:.2f}' y2='{y:.2f}' stroke='#d1d5db' stroke-width='1' />"
        )
        lx, ly = _point(idx, 1.15)
        labels.append(
            f"<text x='{lx:.2f}' y='{ly:.2f}' fill='#4b5563' font-size='11' text-anchor='middle'>{_escape(name)}</text>"
        )
        value = _level_to_value(level) / 5.0
        px, py = _point(idx, value)
        shape_points.append(f"{px:.2f},{py:.2f}")

    profile_polygon = " ".join(shape_points)

    return (
        f"<svg width='{size}' height='{size + 10}' viewBox='0 0 {size} {size + 10}' "
        "xmlns='http://www.w3.org/2000/svg'>"
        f"<text x='{cx:.2f}' y='18' font-size='14' fill='#111827' text-anchor='middle'>{_escape(title)}</text>"
        + "".join(rings)
        + "".join(axis_lines)
        + f"<polygon points='{profile_polygon}' fill='rgba(37,99,235,0.22)' stroke='#2563eb' stroke-width='2' />"
        + "".join(labels)
        + "</svg>"
    )


def _render_overview(profile: Mapping[str, Any]) -> str:
    user = profile.get("user") if isinstance(profile.get("user"), Mapping) else {}
    bio = user.get("bio") if isinstance(user.get("bio"), Mapping) else {}
    state = profile.get("state") if isinstance(profile.get("state"), Mapping) else {}

    rows = [
        ("Name", bio.get("name", "")),
        ("Birth Date", bio.get("birth_date", "")),
        ("Primary Profession", bio.get("primary_profession", "")),
        ("Identity", user.get("identity", "")),
        ("Commitments", user.get("commitments", "")),
        ("Control", user.get("control", "")),
        ("Character", user.get("character", "")),
        ("Condition", state.get("condition", "")),
        ("Context", state.get("context", "")),
    ]
    lines = ["## Character Overview", ""]
    for key, value in rows:
        text = str(value or "").strip() or "(empty)"
        lines.append(f"- **{key}:** {text}")
    return "\n".join(lines)


def _render_role_cards(profile: Mapping[str, Any], templates: Mapping[str, Any]) -> List[RoleCard]:
    roles = profile.get("roles") if isinstance(profile.get("roles"), list) else []
    cards: List[RoleCard] = []

    for role in roles:
        if not isinstance(role, Mapping):
            continue
        name = str(role.get("name") or "Unnamed Role")
        level = str(role.get("level") or "L1")
        description = str(role.get("description") or "")
        radar = role.get("radar") if isinstance(role.get("radar"), Mapping) else {}
        radar_dims = radar.get("dimensions") if isinstance(radar, Mapping) else []
        dims: List[Tuple[str, str]] = []
        if isinstance(radar_dims, list):
            for item in radar_dims:
                if not isinstance(item, Mapping):
                    continue
                dim_name = str(item.get("name") or "").strip()
                if not dim_name:
                    continue
                dims.append((dim_name, str(item.get("level") or "L1")))

        if not dims:
            template_key = str(radar.get("template") or "").strip()
            template = templates.get(template_key) if isinstance(templates, Mapping) else None
            template_dims = template.get("dimensions") if isinstance(template, Mapping) else []
            if isinstance(template_dims, list):
                dims = [(str(dim), "L1") for dim in template_dims if str(dim).strip()]

        achievements = role.get("achievements") if isinstance(role.get("achievements"), list) else []
        achievement_lines = [f"- {item}" for item in achievements if str(item).strip()]
        achievements_markdown = "\n".join(achievement_lines) if achievement_lines else "- (empty)"
        cards.append(
            RoleCard(
                name=name,
                level=level,
                description=description,
                radar_svg=render_radar_svg(title=f"{name} ({level})", dimensions=dims),
                achievements_markdown=achievements_markdown,
            )
        )

    return cards


def _render_inventory(profile: Mapping[str, Any]) -> str:
    inventory = profile.get("inventory") if isinstance(profile.get("inventory"), Mapping) else {}
    role_bags = inventory.get("role_bags") if isinstance(inventory.get("role_bags"), Mapping) else {}

    lines = ["## Achievements & Inventory", ""]
    if not role_bags:
        lines.append("- (empty)")
        return "\n".join(lines)

    for role_name, entries in role_bags.items():
        lines.append(f"### {role_name}")
        if isinstance(entries, list) and entries:
            for entry in entries:
                lines.append(f"- {entry}")
        else:
            lines.append("- (empty)")
        lines.append("")
    return "\n".join(lines).strip()


def _render_projects(profile: Mapping[str, Any]) -> str:
    projects = profile.get("projects") if isinstance(profile.get("projects"), list) else []
    lines = ["## Projects", ""]
    if not projects:
        lines.append("- (empty)")
        return "\n".join(lines)

    for idx, project in enumerate(projects, start=1):
        if not isinstance(project, Mapping):
            continue
        lines.append(f"### {idx}. {project.get('title') or '(untitled)'}")
        lines.append(f"- **Description:** {project.get('description') or '(empty)'}")
        lines.append(f"- **Deadline:** {project.get('deadline') or '(none)'}")
        lines.append(f"- **Status:** {project.get('status') or '(none)'}")
        milestones = project.get("milestones") if isinstance(project.get("milestones"), list) else []
        lines.append("- **Milestones:**")
        if milestones:
            for milestone in milestones:
                lines.append(f"  - {milestone}")
        else:
            lines.append("  - (empty)")
        lines.append("")

    return "\n".join(lines).strip()


def _render_todos(profile: Mapping[str, Any]) -> str:
    todos = profile.get("todos") if isinstance(profile.get("todos"), Mapping) else {}
    lines = ["## TODO", ""]
    for bucket in ("day", "week", "month", "year"):
        lines.append(f"### {bucket.upper()}")
        items = todos.get(bucket)
        if isinstance(items, list) and items:
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                lines.append(
                    "- "
                    f"{item.get('description') or '(empty)'}"
                    f" | deadline={item.get('deadline') or '-'}"
                    f" | status={item.get('status') or 'todo'}"
                )
        else:
            lines.append("- (empty)")
        lines.append("")
    return "\n".join(lines).strip()


def build_panel_snapshot(profile: Mapping[str, Any], templates: Mapping[str, Any]) -> PanelSnapshot:
    return PanelSnapshot(
        overview_markdown=_render_overview(profile),
        role_cards=_render_role_cards(profile, templates),
        inventory_markdown=_render_inventory(profile),
        projects_markdown=_render_projects(profile),
        todos_markdown=_render_todos(profile),
    )


def _parse_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "enabled"}:
            return True
        if lowered in {"0", "false", "no", "off", "disabled"}:
            return False
    return bool(value)


def _parse_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _display_host(host: str) -> str:
    normalized = str(host or "").strip() or "127.0.0.1"
    if normalized == "0.0.0.0":
        return "127.0.0.1"
    return normalized


def _render_roles_html(cards: Iterable[RoleCard]) -> str:
    sections: List[str] = []
    for card in cards:
        achievements = [
            line[2:].strip()
            for line in str(card.achievements_markdown or "").splitlines()
            if line.strip().startswith("- ")
        ]
        achievements_html = "".join(f"<li>{_escape(item)}</li>" for item in achievements) or (
            "<li class='liferpg-muted'>(empty)</li>"
        )
        sections.append(
            "<section class='liferpg-card liferpg-role-card'>"
            "<div class='liferpg-eyebrow'>Role</div>"
            f"<h2 class='liferpg-section-title'>{_escape(card.name)}</h2>"
            f"<p class='liferpg-field-value'>{_escape(card.description or '(empty)')}</p>"
            "<div class='liferpg-meta-row'>"
            f"<span class='liferpg-meta-tag'>Level {_escape(card.level)}</span>"
            "</div>"
            f"{card.radar_svg}"
            "<div class='liferpg-field'>"
            "<span class='liferpg-field-label'>Achievements</span>"
            f"<ul class='liferpg-list'>{achievements_html}</ul>"
            "</div>"
            "</section>"
        )
    if not sections:
        body_html = "<section class='liferpg-card'><p class='liferpg-muted'>(no roles)</p></section>"
    else:
        body_html = f"<div class='liferpg-role-grid'>{''.join(sections)}</div>"
    return (
        "<section id='roles' class='liferpg-shell liferpg-section'>"
        "<div class='liferpg-section-header'>"
        "<div class='liferpg-eyebrow'>Roles</div>"
        "<h2 class='liferpg-section-title'>Role Panels and Radar Views</h2>"
        "<p class='liferpg-section-subtitle'>Each role is rendered as its own growth surface with level, radar, and concrete achievements.</p>"
        "</div>"
        f"{body_html}"
        "</section>"
    )


def _resolve_panel_cfg(config_dict: Mapping[str, Any] | None) -> Dict[str, Any]:
    cfg = dict((config_dict or {}).get("liferpg_config") or {})
    panel_cfg = cfg.get("panel") if isinstance(cfg.get("panel"), Mapping) else {}
    cfg["panel"] = dict(panel_cfg)
    return cfg


def _build_store_from_config(config_dict: Mapping[str, Any] | None) -> LifeRPGStore:
    cfg = _resolve_panel_cfg(config_dict)
    return LifeRPGStore(
        base_dir=str(cfg.get("base_dir") or "storage/liferpg"),
        profile_filename=str(cfg.get("profile_filename") or "liferpg.yaml"),
        templates_filename=str(cfg.get("templates_filename") or "radar_templates.yaml"),
        history_filename=str(cfg.get("history_filename") or "history.md"),
        state_filename=str(cfg.get("state_filename") or "runtime_state.yaml"),
    )


def _is_enabled(config_dict: Mapping[str, Any] | None) -> bool:
    cfg = _resolve_panel_cfg(config_dict)
    raw = cfg.get("enabled", True)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() not in {"0", "false", "no", "off", "disabled"}
    return bool(raw)


def is_liferpg_separate_page_enabled(config_dict: Mapping[str, Any] | None) -> bool:
    if not _is_enabled(config_dict):
        return False
    cfg = _resolve_panel_cfg(config_dict)
    panel_cfg = cfg.get("panel") if isinstance(cfg.get("panel"), Mapping) else {}
    return _parse_bool(panel_cfg.get("separate_page"), default=False)


def get_liferpg_page_url(config_dict: Mapping[str, Any] | None) -> Optional[str]:
    if not is_liferpg_separate_page_enabled(config_dict):
        return None
    cfg = _resolve_panel_cfg(config_dict)
    panel_cfg = cfg.get("panel") if isinstance(cfg.get("panel"), Mapping) else {}
    host = _display_host(str(panel_cfg.get("server_name") or "127.0.0.1"))
    port = _parse_int(panel_cfg.get("server_port"), default=7862)
    return f"http://{host}:{port}"


def get_dialogue_page_url(config_dict: Mapping[str, Any] | None) -> Optional[str]:
    cfg = dict(config_dict or {})

    realtime_cfg = cfg.get("realtime_config") if isinstance(cfg.get("realtime_config"), Mapping) else {}
    if realtime_cfg and _parse_bool(realtime_cfg.get("enabled"), default=False):
        host = _display_host(str(realtime_cfg.get("server_name") or "127.0.0.1"))
        port = _parse_int(realtime_cfg.get("server_port"), default=7860)
        return f"http://{host}:{port}"

    gradio_cfg = cfg.get("gradio_config") if isinstance(cfg.get("gradio_config"), Mapping) else {}
    if gradio_cfg and _parse_bool(gradio_cfg.get("enabled"), default=False):
        host = _display_host(str(gradio_cfg.get("server_name") or "127.0.0.1"))
        port = _parse_int(gradio_cfg.get("server_port"), default=7860)
        return f"http://{host}:{port}"

    return None


def _panel_header_html(
    profile: Mapping[str, Any],
    *,
    style_name: str,
    icon_pack: str,
    dialogue_url: Optional[str] = None,
) -> str:
    user = profile.get("user") if isinstance(profile.get("user"), Mapping) else {}
    bio = user.get("bio") if isinstance(user.get("bio"), Mapping) else {}
    state = profile.get("state") if isinstance(profile.get("state"), Mapping) else {}
    roles = profile.get("roles") if isinstance(profile.get("roles"), list) else []
    projects = profile.get("projects") if isinstance(profile.get("projects"), list) else []
    inventory = profile.get("inventory") if isinstance(profile.get("inventory"), Mapping) else {}
    role_bags_raw = inventory.get("role_bags")
    role_bags = role_bags_raw if isinstance(role_bags_raw, Mapping) else {}
    items_count = sum(len(entries) for entries in role_bags.values() if isinstance(entries, list))
    todos = profile.get("todos") if isinstance(profile.get("todos"), Mapping) else {}
    todo_count = sum(
        len(entries)
        for bucket in ("day", "week", "month", "year")
        for entries in [todos.get(bucket)]
        if isinstance(entries, list)
    )
    name = str(bio.get("name") or "Unknown User")
    profession = str(bio.get("primary_profession") or "Unknown Profession")
    birth_date = str(bio.get("birth_date") or "").strip()
    age_text = ""
    try:
        if birth_date:
            born = datetime.fromisoformat(birth_date).date()
            today = datetime.now().date()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            if age >= 0:
                age_text = f"{age} years old"
    except Exception:
        age_text = ""
    subtitle_parts = [profession]
    if age_text:
        subtitle_parts.append(age_text)
    identity = str(user.get("identity") or "").strip() or "(empty)"
    condition = str(state.get("condition") or "").strip() or "(empty)"
    context = str(state.get("context") or "").strip() or "(empty)"
    refreshed = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    dialogue_link_html = (
        f"<a class='liferpg-nav-primary' href='{_escape(dialogue_url)}' target='_blank' rel='noopener'>Open Dialogue</a>"
        if dialogue_url
        else ""
    )
    section_links_html = "".join(
        f"<a class='liferpg-nav-link' href='{anchor}'>{label}</a>"
        for anchor, label in (
            ("#overview", "Overview"),
            ("#roles", "Roles"),
            ("#inventory", "Inventory"),
            ("#projects", "Projects"),
            ("#todos", "TODO"),
        )
    )

    return (
        "<div class='liferpg-shell liferpg-stack'>"
        "<section class='liferpg-masthead liferpg-section'>"
        "<div class='liferpg-card liferpg-masthead-card'>"
        "<div class='liferpg-eyebrow'>LifeRPG Dashboard</div>"
        f"<h1 class='liferpg-page-title'>{_escape(name)}</h1>"
        f"<p class='liferpg-page-subtitle'>{_escape(' · '.join(subtitle_parts))}</p>"
        f"<p class='liferpg-field-value'>{_escape(identity)}</p>"
        "<div class='liferpg-nav'>"
        f"{dialogue_link_html}"
        f"{section_links_html}"
        "</div>"
        "<p class='liferpg-route-note'>"
        "A standalone growth panel for long-horizon identity, roles, projects, and operating state."
        "</p>"
        "</div>"
        "<div class='liferpg-card liferpg-card-alt liferpg-sidebar-card'>"
        "<div>"
        "<h2 class='liferpg-section-title'>Current State</h2>"
        "<div class='liferpg-field'><span class='liferpg-field-label'>Condition</span>"
        f"<p class='liferpg-field-value'>{_escape(condition)}</p></div>"
        "<div class='liferpg-field'><span class='liferpg-field-label'>Context</span>"
        f"<p class='liferpg-field-value'>{_escape(context)}</p></div>"
        "</div>"
        "<div class='liferpg-pill-row'>"
        f"<span class='liferpg-pill'>style {_escape(style_name)}</span>"
        f"<span class='liferpg-pill'>icon pack {_escape(icon_pack)}</span>"
        f"<span class='liferpg-pill'>refreshed {_escape(refreshed)}</span>"
        "</div>"
        "</div>"
        "</section>"
        "<section class='liferpg-hero liferpg-section'>"
        "<div class='liferpg-card'>"
        "<div class='liferpg-section-header'>"
        "<div class='liferpg-eyebrow'>Profile</div>"
        "<h2 class='liferpg-section-title'>Growth Snapshot</h2>"
        "<p class='liferpg-section-subtitle'>A quick read on identity, active work, and what is being carried right now.</p>"
        "</div>"
        "<div class='liferpg-kpi-row'>"
        f"<div class='liferpg-kpi'><span class='liferpg-kpi-label'>Roles</span><span class='liferpg-kpi-value'>{len(roles)}</span></div>"
        f"<div class='liferpg-kpi'><span class='liferpg-kpi-label'>Projects</span><span class='liferpg-kpi-value'>{len(projects)}</span></div>"
        f"<div class='liferpg-kpi'><span class='liferpg-kpi-label'>Inventory</span><span class='liferpg-kpi-value'>{items_count}</span></div>"
        f"<div class='liferpg-kpi'><span class='liferpg-kpi-label'>TODO</span><span class='liferpg-kpi-value'>{todo_count}</span></div>"
        "</div>"
        "</div>"
        "<div class='liferpg-card'>"
        "<div class='liferpg-section-header'>"
        "<div class='liferpg-eyebrow'>Frame</div>"
        "<h2 class='liferpg-section-title'>Panel Intent</h2>"
        "<p class='liferpg-section-subtitle'>This page is optimized for long-term coherence rather than turn-by-turn memory details.</p>"
        "</div>"
        "<p class='liferpg-field-value'>Use it to track who the user is, what roles are growing, what projects matter, and what deadlines are active.</p>"
        "</div>"
        "</section>"
        "</div>"
    )


def _overview_dashboard_html(profile: Mapping[str, Any]) -> str:
    user = profile.get("user") if isinstance(profile.get("user"), Mapping) else {}
    return (
        "<section id='overview' class='liferpg-shell liferpg-section'>"
        "<div class='liferpg-section-header'>"
        "<div class='liferpg-eyebrow'>Overview</div>"
        "<h2 class='liferpg-section-title'>Identity and Operating Principles</h2>"
        "<p class='liferpg-section-subtitle'>Stable self-description and constraints that should guide the assistant over time.</p>"
        "</div>"
        "<div class='liferpg-grid-2'>"
        "<section class='liferpg-card'>"
        "<h2 class='liferpg-section-title'>Identity</h2>"
        "<div class='liferpg-field'><span class='liferpg-field-label'>Self statement</span>"
        f"<p class='liferpg-field-value'>{_escape(str(user.get('identity') or '').strip() or '(empty)')}</p></div>"
        "</section>"
        "<section class='liferpg-card'>"
        "<h2 class='liferpg-section-title'>Operating Principles</h2>"
        "<div class='liferpg-field'><span class='liferpg-field-label'>Commitments</span>"
        f"<p class='liferpg-field-value'>{_escape(str(user.get('commitments') or '').strip() or '(empty)')}</p></div>"
        "<div class='liferpg-field'><span class='liferpg-field-label'>Control</span>"
        f"<p class='liferpg-field-value'>{_escape(str(user.get('control') or '').strip() or '(empty)')}</p></div>"
        "<div class='liferpg-field'><span class='liferpg-field-label'>Character</span>"
        f"<p class='liferpg-field-value'>{_escape(str(user.get('character') or '').strip() or '(empty)')}</p></div>"
        "</section>"
        "</div>"
        "</section>"
    )


def _inventory_dashboard_html(profile: Mapping[str, Any]) -> str:
    inventory = profile.get("inventory") if isinstance(profile.get("inventory"), Mapping) else {}
    role_bags = inventory.get("role_bags") if isinstance(inventory.get("role_bags"), Mapping) else {}
    sections = [
        "<section id='inventory' class='liferpg-shell liferpg-section'>"
        "<div class='liferpg-section-header'>"
        "<div class='liferpg-eyebrow'>Inventory</div>"
        "<h2 class='liferpg-section-title'>Artifacts and Achievements</h2>"
        "<p class='liferpg-section-subtitle'>Concrete outputs carried by each role, rather than vague self-evaluations.</p>"
        "</div>"
        "<section class='liferpg-card'>"
        "<h2 class='liferpg-section-title'>Achievements & Inventory</h2>"
    ]
    if not role_bags:
        sections.append("<p class='liferpg-muted'>(empty)</p>")
    for role_name, entries in role_bags.items():
        sections.append("<div class='liferpg-bag-card'>")
        sections.append(f"<h3 class='liferpg-bag-title'>{_escape(role_name)}</h3>")
        if isinstance(entries, list) and entries:
            sections.append("<ul class='liferpg-list'>")
            for entry in entries:
                sections.append(f"<li>{_escape(entry)}</li>")
            sections.append("</ul>")
        else:
            sections.append("<p class='liferpg-bag-body liferpg-muted'>(empty)</p>")
        sections.append("</div>")
    sections.append("</section></section>")
    return "".join(sections)


def _projects_dashboard_html(profile: Mapping[str, Any]) -> str:
    projects = profile.get("projects") if isinstance(profile.get("projects"), list) else []
    sections = [
        "<section id='projects' class='liferpg-shell liferpg-section'>"
        "<div class='liferpg-section-header'>"
        "<div class='liferpg-eyebrow'>Projects</div>"
        "<h2 class='liferpg-section-title'>Active Long-Horizon Work</h2>"
        "<p class='liferpg-section-subtitle'>The projects that currently define the user's growth trajectory.</p>"
        "</div>"
        "<section class='liferpg-card'>"
        "<h2 class='liferpg-section-title'>Projects</h2>"
    ]
    if not projects:
        sections.append("<p class='liferpg-muted'>(empty)</p>")
    for project in projects:
        if not isinstance(project, Mapping):
            continue
        sections.append("<div class='liferpg-project-card'>")
        sections.append(
            f"<h3 class='liferpg-project-title'>{_escape(project.get('title') or '(untitled)')}</h3>"
        )
        sections.append(
            f"<p class='liferpg-project-body'>{_escape(project.get('description') or '(empty)')}</p>"
        )
        sections.append("<div class='liferpg-meta-row'>")
        sections.append(
            f"<span class='liferpg-meta-tag'>deadline {_escape(project.get('deadline') or '-')}</span>"
        )
        sections.append(
            f"<span class='liferpg-meta-tag'>status {_escape(project.get('status') or '-')}</span>"
        )
        sections.append("</div>")
        milestones = project.get("milestones") if isinstance(project.get("milestones"), list) else []
        if milestones:
            sections.append("<ul class='liferpg-list'>")
            for milestone in milestones:
                sections.append(f"<li>{_escape(milestone)}</li>")
            sections.append("</ul>")
        sections.append("</div>")
    sections.append("</section></section>")
    return "".join(sections)


def _todos_dashboard_html(profile: Mapping[str, Any]) -> str:
    todos = profile.get("todos") if isinstance(profile.get("todos"), Mapping) else {}
    sections = [
        "<section id='todos' class='liferpg-shell liferpg-section'>"
        "<div class='liferpg-section-header'>"
        "<div class='liferpg-eyebrow'>Execution</div>"
        "<h2 class='liferpg-section-title'>Time-Bucketed TODO</h2>"
        "<p class='liferpg-section-subtitle'>A simple control surface for immediate and mid-horizon commitments.</p>"
        "</div>"
        "<div class='liferpg-todo-grid'>"
    ]
    for bucket in ("day", "week", "month", "year"):
        sections.append("<section class='liferpg-card liferpg-todo-column'>")
        sections.append(f"<h2 class='liferpg-section-title'>{bucket.upper()}</h2>")
        entries = todos.get(bucket)
        if isinstance(entries, list) and entries:
            sections.append("<ul class='liferpg-list'>")
            for entry in entries:
                if not isinstance(entry, Mapping):
                    continue
                sections.append(
                    "<li>"
                    f"<p class='liferpg-todo-title'>{_escape(entry.get('description') or '(empty)')}</p>"
                    f"<p class='liferpg-project-body'>deadline {_escape(entry.get('deadline') or '-')} · status {_escape(entry.get('status') or 'todo')}</p>"
                    "</li>"
                )
            sections.append("</ul>")
        else:
            sections.append("<p class='liferpg-muted'>(empty)</p>")
        sections.append("</section>")
    sections.append("</div></section>")
    return "".join(sections)


def _build_dashboard_outputs(
    profile: Mapping[str, Any],
    templates: Mapping[str, Any],
    *,
    style_name: str,
    icon_pack: str,
    dialogue_url: Optional[str],
) -> Tuple[str, str, str, str, str, str]:
    snapshot = build_panel_snapshot(profile, templates)
    return (
        _panel_header_html(
            profile,
            style_name=style_name,
            icon_pack=icon_pack,
            dialogue_url=dialogue_url,
        ),
        _overview_dashboard_html(profile),
        _render_roles_html(snapshot.role_cards),
        _inventory_dashboard_html(profile),
        _projects_dashboard_html(profile),
        _todos_dashboard_html(profile),
    )


def _build_liferpg_launch_kwargs(
    config_dict: Mapping[str, Any] | None,
    *,
    prevent_thread_lock: bool = False,
) -> Dict[str, Any]:
    cfg = _resolve_panel_cfg(config_dict)
    panel_cfg = cfg.get("panel") if isinstance(cfg.get("panel"), Mapping) else {}
    kwargs: Dict[str, Any] = {"share": _parse_bool(panel_cfg.get("share"), default=False)}
    server_name = panel_cfg.get("server_name")
    if server_name:
        kwargs["server_name"] = str(server_name)
    server_port = panel_cfg.get("server_port")
    if server_port is not None and str(server_port).strip() != "":
        kwargs["server_port"] = int(server_port)
    if prevent_thread_lock:
        kwargs["prevent_thread_lock"] = True
    return kwargs


def _extract_launch_urls(launch_result: Any) -> Tuple[Optional[str], Optional[str]]:
    local_url: Optional[str] = None
    share_url: Optional[str] = None
    if isinstance(launch_result, tuple):
        if len(launch_result) >= 2 and isinstance(launch_result[1], str):
            local_url = launch_result[1]
        if len(launch_result) >= 3 and isinstance(launch_result[2], str):
            share_url = launch_result[2]
        return local_url, share_url
    local_candidate = getattr(launch_result, "local_url", None)
    share_candidate = getattr(launch_result, "share_url", None)
    if isinstance(local_candidate, str):
        local_url = local_candidate
    if isinstance(share_candidate, str):
        share_url = share_candidate
    return local_url, share_url


def _log_launch_urls(launch_result: Any) -> None:
    local_url, share_url = _extract_launch_urls(launch_result)
    if local_url:
        logger.info("LifeRPG UI URL: %s", local_url)
    if share_url:
        logger.info("LifeRPG UI share URL: %s", share_url)


def _build_liferpg_dashboard_components(
    *,
    gr: Any,
    config_dict: Mapping[str, Any] | None,
) -> LifeRPGPanelComponents:
    cfg = _resolve_panel_cfg(config_dict)
    panel_cfg = cfg.get("panel") if isinstance(cfg.get("panel"), Mapping) else {}
    style_name = str(panel_cfg.get("style") or "minimal")
    icon_pack = str(panel_cfg.get("icon_pack") or "default")
    dialogue_url = get_dialogue_page_url(config_dict)
    store = _build_store_from_config(config_dict)
    default_profile = cfg.get("default_profile") if isinstance(cfg.get("default_profile"), Mapping) else None
    store.ensure_initialized(default_profile=default_profile)

    def _refresh() -> Tuple[str, str, str, str, str, str]:
        profile = store.read_profile()
        templates = store.read_templates()
        return _build_dashboard_outputs(
            profile,
            templates,
            style_name=style_name,
            icon_pack=icon_pack,
            dialogue_url=dialogue_url,
        )

    initial_header, initial_overview, initial_roles, initial_inventory, initial_projects, initial_todos = _refresh()
    gr.HTML(f"<style>{_LIFERPG_CSS}</style>")
    header = gr.HTML(initial_header, elem_id="liferpg-header")
    overview_html = gr.HTML(initial_overview, elem_id="liferpg-overview")
    roles_html = gr.HTML(initial_roles, elem_id="liferpg-roles")
    with gr.Row():
        inventory_html = gr.HTML(initial_inventory, elem_id="liferpg-inventory")
        projects_html = gr.HTML(initial_projects, elem_id="liferpg-projects")
    todos_html = gr.HTML(initial_todos, elem_id="liferpg-todos")
    refresh_btn = gr.Button("Refresh LifeRPG", variant="secondary")
    outputs = [header, overview_html, roles_html, inventory_html, projects_html, todos_html]
    refresh_btn.click(_refresh, outputs=outputs, queue=False)
    return LifeRPGPanelComponents(refresh_fn=_refresh, outputs=outputs)


def build_liferpg_standalone_app(*, config_dict: Mapping[str, Any] | None) -> Any:
    import gradio as gr

    with gr.Blocks(title="LifeRPG Dashboard", css=_LIFERPG_CSS) as demo:
        _build_liferpg_dashboard_components(gr=gr, config_dict=config_dict)
    return demo


def launch_liferpg_standalone_app(
    *,
    config_dict: Mapping[str, Any] | None,
    prevent_thread_lock: bool = False,
) -> Any:
    demo = build_liferpg_standalone_app(config_dict=config_dict)
    launch_kwargs = _build_liferpg_launch_kwargs(
        config_dict,
        prevent_thread_lock=prevent_thread_lock,
    )
    try:
        launch_result = demo.launch(**launch_kwargs)
        _log_launch_urls(launch_result)
        return demo
    except OSError as exc:
        cfg = _resolve_panel_cfg(config_dict)
        panel_cfg = cfg.get("panel") if isinstance(cfg.get("panel"), Mapping) else {}
        configured_port = launch_kwargs.get("server_port")
        fallback_enabled = _parse_bool(
            panel_cfg.get("server_port_auto_fallback_on_conflict"),
            default=True,
        )
        if not (
            fallback_enabled
            and configured_port is not None
            and "Cannot find empty port in range" in str(exc)
        ):
            raise
        retry_kwargs = dict(launch_kwargs)
        retry_kwargs.pop("server_port", None)
        logger.warning(
            "Configured LifeRPG UI port %s is occupied; retrying with auto-selected free port.",
            configured_port,
        )
        launch_result = demo.launch(**retry_kwargs)
        _log_launch_urls(launch_result)
        return demo


def build_liferpg_panel(*, gr: Any, config_dict: Mapping[str, Any] | None) -> LifeRPGPanelComponents | None:
    if not _is_enabled(config_dict) or is_liferpg_separate_page_enabled(config_dict):
        return None

    with gr.Tab("LifeRPG"):
        return _build_liferpg_dashboard_components(gr=gr, config_dict=config_dict)
