from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class _IntentProfile:
    wants_upload: bool
    wants_form: bool
    wants_chart: bool
    wants_chat: bool
    chart_type: str
    wants_multi_step: bool
    wants_export: bool
    wants_table: bool
    wants_progress: bool
    wants_kanban: bool
    wants_timeline: bool
    wants_calendar: bool
    wants_media: bool
    wants_chat_clear_action: bool
    wants_chat_help_action: bool
    theme_mode: Optional[str]
    requested_order: tuple[str, ...]
    chart_values: tuple[float, ...]


def _token_hit(text: str, tokens: Set[str]) -> bool:
    lowered = text.lower()
    return any(_contains_token(lowered, token.lower()) for token in tokens)


def _contains_token(text: str, token: str) -> bool:
    if not token:
        return False
    if not _is_ascii_token(token):
        return token in text
    pattern = _ascii_token_pattern(token)
    return bool(pattern.search(text))


@lru_cache(maxsize=512)
def _ascii_token_pattern(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")


def _is_ascii_token(token: str) -> bool:
    for ch in token:
        if ch == " ":
            continue
        if not ("a" <= ch <= "z" or "0" <= ch <= "9" or ch in {"_", "-"}):
            return False
    return True


_INTENT_TOKENS: Dict[str, Set[str]] = {
    "chat": {
        "chat",
        "chat window",
        "conversation",
        "dialog",
        "assistant",
        "message",
        "messaging",
        "qq",
        "im",
        "聊天",
        "聊天窗口",
        "对话",
        "会话",
        "问答",
        "客服",
        "即时通讯",
    },
    "upload": {
        "upload",
        "uploader",
        "file upload",
        "upload file",
        "csv",
        "excel",
        "xlsx",
        "drag and drop",
        "上传",
        "上传文件",
        "拖拽上传",
    },
    "table": {"table", "grid", "sheet", "rows", "表格", "清单", "数据表", "明细表"},
    "chart": {
        "chart",
        "plot",
        "graph",
        "visual",
        "line",
        "bar",
        "图",
        "图表",
        "折线",
        "柱状",
        "可视化",
        "分析",
    },
    "line_chart": {"line", "trend", "timeseries", "折线"},
    "form": {
        "form",
        "intake",
        "input",
        "collect",
        "registration",
        "onboarding",
        "application form",
        "questionnaire",
        "填写",
        "收集",
        "表单",
        "登记",
        "登记表",
        "申请",
        "申请表",
        "录入",
        "问卷",
        "填表",
        "入职登记",
        "员工入职",
        "入职表",
        "员工登记",
        "信息采集",
        "入职",
    },
    "wizard": {"multi-step", "wizard", "step", "流程", "多步"},
    "progress": {"progress", "status", "pipeline", "进度", "状态"},
    "export": {"export", "download", "report", "导出", "下载", "报告"},
    "dashboard": {"dashboard", "workbench", "workspace", "看板", "工作台", "控制台"},
    "kanban": {"kanban", "scrum", "backlog", "看板"},
    "timeline": {"timeline", "roadmap", "milestone", "时间线", "路线图", "里程碑"},
    "calendar": {"calendar", "schedule", "agenda", "日历", "排期", "日程"},
    "media": {"media", "audio", "video", "podcast", "music", "媒体", "音频", "视频", "音乐", "播放"},
    "clear_action": {
        "clear",
        "clear message",
        "clear chat",
        "reset",
        "wipe",
        "清空",
        "清空消息",
        "清空聊天",
        "重置",
    },
    "help_action": {"help", "usage", "guide", "说明", "帮助", "使用说明"},
    "theme_dark": {"dark", "dark mode", "dark theme", "night", "深色", "暗色", "黑色"},
    "theme_light": {"light", "light mode", "light theme", "day", "浅色", "亮色", "白色"},
}

_COMPONENT_HINT_KEYS: tuple[str, ...] = (
    "chat",
    "upload",
    "table",
    "chart",
    "form",
    "wizard",
    "progress",
    "export",
    "kanban",
    "timeline",
    "calendar",
    "media",
)


def _tokens(name: str) -> Set[str]:
    return _INTENT_TOKENS[name]


def _extract_focus_text(text: str) -> str:
    if not text:
        return ""
    direct_patterns = (
        r"(?:改成|换成|改为|变成|切换到|只要|我要|给我|做成|生成)\s*[:：]?\s*(.+)$",
        r"(?:switch\s+to|change\s+to|convert\s+to|build|create)\s*[:：]?\s*(.+)$",
    )
    for pattern in direct_patterns:
        matched = re.search(pattern, text, flags=re.IGNORECASE)
        if not matched:
            continue
        candidate = matched.group(1).strip().strip("。.!?！？")
        if len(candidate.replace(" ", "")) >= 2:
            return candidate

    parts = [
        segment.strip()
        for segment in re.split(r"[。.!?！？\n\r]+", text)
        if segment and segment.strip()
    ]
    if not parts:
        return text
    for segment in reversed(parts):
        if len(segment.replace(" ", "")) >= 2:
            return segment
    return parts[-1]


def _has_component_signal(text: str) -> bool:
    for key in _COMPONENT_HINT_KEYS:
        if _token_hit(text, _tokens(key)):
            return True
    return False


def intent_has_component_signals(intent: str) -> bool:
    text = (intent or "").strip().lower()
    if not text:
        return False
    focused = _extract_focus_text(text)
    return _has_component_signal(focused) or _has_component_signal(text)


def _extract_requested_order(text: str) -> tuple[str, ...]:
    located: list[tuple[int, str]] = []
    for key in _COMPONENT_HINT_KEYS:
        tokens = _tokens(key)
        first_index = -1
        for token in tokens:
            idx = text.find(token)
            if idx < 0:
                continue
            if first_index < 0 or idx < first_index:
                first_index = idx
        if first_index >= 0:
            located.append((first_index, key))
    located.sort(key=lambda item: item[0])
    return tuple(key for _, key in located)


def _extract_chart_values(text: str) -> tuple[float, ...]:
    # Prefer explicit value phrases first (e.g. "数据: 5,8,13,21").
    candidates: list[str] = []
    marked = re.findall(r"(?:data|values?|数据|序列)\s*[:：]\s*([0-9\.\-\+\s,，;；]+)", text)
    candidates.extend(marked)

    # Also allow explicit numeric lists in the prompt body.
    inferred = re.findall(r"(?:[-+]?\d+(?:\.\d+)?\s*[,，;；]\s*){2,}[-+]?\d+(?:\.\d+)?", text)
    candidates.extend(inferred)

    for raw in candidates:
        numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", raw)
        if len(numbers) < 2:
            continue
        parsed: list[float] = []
        for item in numbers:
            try:
                parsed.append(float(item))
            except Exception:
                parsed = []
                break
        if 2 <= len(parsed) <= 48:
            return tuple(parsed)
    return ()


def _detect_chat_actions(signal_text: str, *, wants_chat: bool) -> tuple[bool, bool]:
    if not wants_chat:
        return False, False
    wants_clear = _token_hit(signal_text, _tokens("clear_action"))
    wants_help = _token_hit(signal_text, _tokens("help_action"))
    return wants_clear, wants_help


def _detect_theme_mode(signal_text: str) -> Optional[str]:
    if _token_hit(signal_text, _tokens("theme_dark")):
        return "dark"
    if _token_hit(signal_text, _tokens("theme_light")):
        return "light"
    return None


def _analyze_intent(intent: str) -> _IntentProfile:
    text = (intent or "").strip().lower()
    focused = _extract_focus_text(text)
    signal_text = focused if _has_component_signal(focused) else text
    if not text:
        return _IntentProfile(
            wants_upload=True,
            wants_form=False,
            wants_chart=True,
            wants_chat=False,
            chart_type="bar",
            wants_multi_step=False,
            wants_export=True,
            wants_table=True,
            wants_progress=True,
            wants_kanban=False,
            wants_timeline=False,
            wants_calendar=False,
            wants_media=False,
            wants_chat_clear_action=False,
            wants_chat_help_action=False,
            theme_mode=None,
            requested_order=(),
            chart_values=(),
        )

    wants_upload = _token_hit(signal_text, _tokens("upload"))
    wants_form = _token_hit(signal_text, _tokens("form"))
    wants_chart = _token_hit(signal_text, _tokens("chart"))
    wants_chat = _token_hit(signal_text, _tokens("chat"))
    chart_type = "line" if _token_hit(signal_text, _tokens("line_chart")) else "bar"
    wants_multi_step = _token_hit(signal_text, _tokens("wizard"))
    wants_export = _token_hit(signal_text, _tokens("export"))
    wants_table = _token_hit(signal_text, _tokens("table"))
    wants_progress = _token_hit(signal_text, _tokens("progress"))
    wants_dashboard = _token_hit(signal_text, _tokens("dashboard"))
    wants_kanban = _token_hit(signal_text, _tokens("kanban"))
    wants_timeline = _token_hit(signal_text, _tokens("timeline"))
    wants_calendar = _token_hit(signal_text, _tokens("calendar"))
    wants_media = _token_hit(signal_text, _tokens("media"))
    wants_chat_clear_action, wants_chat_help_action = _detect_chat_actions(
        signal_text,
        wants_chat=wants_chat,
    )
    theme_mode = _detect_theme_mode(signal_text)

    if (wants_upload and wants_chart) or (wants_dashboard and (wants_upload or wants_chart)):
        wants_table = True
    if wants_kanban or wants_calendar:
        wants_table = True
    if wants_timeline:
        wants_chart = True
        wants_table = True

    if (wants_upload or wants_multi_step) and not wants_progress:
        wants_progress = True
    if wants_multi_step and not wants_export:
        wants_export = True

    if not (wants_upload or wants_form or wants_chart or wants_table or wants_chat):
        # Generic fallback: keep it lightweight and interactive instead of forcing a data-table workspace.
        wants_form = True

    return _IntentProfile(
        wants_upload=wants_upload,
        wants_form=wants_form,
        wants_chart=wants_chart,
        wants_chat=wants_chat,
        chart_type=chart_type,
        wants_multi_step=wants_multi_step,
        wants_export=wants_export,
        wants_table=wants_table,
        wants_progress=wants_progress,
        wants_kanban=wants_kanban,
        wants_timeline=wants_timeline,
        wants_calendar=wants_calendar,
        wants_media=wants_media,
        wants_chat_clear_action=wants_chat_clear_action,
        wants_chat_help_action=wants_chat_help_action,
        theme_mode=theme_mode,
        requested_order=_extract_requested_order(signal_text),
        chart_values=_extract_chart_values(signal_text),
    )


def _resolve_mode(profile: _IntentProfile) -> str:
    if profile.wants_kanban:
        return "kanban"
    if profile.wants_timeline:
        return "timeline"
    if profile.wants_calendar:
        return "calendar"
    if profile.wants_media:
        return "media"
    if profile.wants_chat and not (
        profile.wants_upload
        or profile.wants_table
        or profile.wants_chart
        or profile.wants_form
        or profile.wants_multi_step
    ):
        return "chat"
    if profile.wants_multi_step:
        return "workflow"
    if profile.wants_form and not (profile.wants_upload or profile.wants_chart or profile.wants_table):
        return "intake"
    if profile.wants_upload or profile.wants_chart or profile.wants_table:
        return "analytics"
    return "generic"


def _to_compact_number(value: float) -> int | float:
    if int(value) == value:
        return int(value)
    return value


def _inject_chart_values(components: List[Dict[str, Any]], values: tuple[float, ...]) -> None:
    if not values:
        return
    labels = [str(index + 1) for index in range(len(values))]
    compact_values = [_to_compact_number(item) for item in values]
    for component in components:
        if component.get("type") != "chart":
            continue
        props = component.get("props")
        if not isinstance(props, dict):
            props = {}
            component["props"] = props
        props["labels"] = labels
        props["values"] = compact_values


_ORDER_BUCKETS: Dict[str, tuple[str, ...]] = {
    "upload": ("uploader",),
    "table": ("table_main", "timeline_table", "calendar_table", "kanban_todo", "kanban_doing", "kanban_done"),
    "chart": ("chart_main", "timeline_chart"),
    "form": ("form_main", "calendar_form", "media_control"),
    "wizard": ("wizard_main",),
    "chat": ("chat_main",),
    "progress": ("progress_main",),
    "export": ("export_main",),
    "kanban": ("kanban_board", "kanban_todo", "kanban_doing", "kanban_done"),
    "timeline": ("timeline_chart", "timeline_table"),
    "calendar": ("calendar_form", "calendar_table"),
    "media": ("media_control", "media_status"),
}


def _reorder_root(root: List[str], requested_order: tuple[str, ...]) -> List[str]:
    if not requested_order:
        return root

    root_set = set(root)
    ordered: List[str] = []
    for key in requested_order:
        for component_id in _ORDER_BUCKETS.get(key, ()):
            if component_id in root_set and component_id not in ordered:
                ordered.append(component_id)

    for component_id in root:
        if component_id != "intro" and component_id not in ordered:
            ordered.append(component_id)

    if "intro" in root_set:
        return ["intro"] + ordered
    return ordered


def _component_id_set(components: List[Dict[str, Any]]) -> Set[str]:
    ids: Set[str] = set()
    for component in components:
        component_id = component.get("id")
        if isinstance(component_id, str) and component_id.strip():
            ids.add(component_id.strip())
    return ids


def _append_component_if_missing(
    components: List[Dict[str, Any]],
    root: List[str],
    component: Dict[str, Any],
    *,
    root_entry: str | None = None,
    add_to_root: bool = True,
) -> None:
    component_id = str(component.get("id") or "").strip()
    if not component_id:
        return
    existing = _component_id_set(components)
    if component_id not in existing:
        components.append(component)
    if add_to_root:
        target_root = root_entry or component_id
        if target_root not in root:
            root.append(target_root)


def _ensure_requested_components(profile: _IntentProfile, components: List[Dict[str, Any]], root: List[str]) -> None:
    for key in profile.requested_order:
        if key == "chat":
            _append_component_if_missing(components, root, _chat_component())
            continue
        if key == "upload":
            _append_component_if_missing(components, root, _upload_component())
            continue
        if key == "table":
            _append_component_if_missing(components, root, _table_component())
            continue
        if key == "chart":
            _append_component_if_missing(components, root, _chart_component(chart_type=profile.chart_type))
            continue
        if key == "form":
            _append_component_if_missing(components, root, _form_component())
            continue
        if key == "wizard":
            _append_component_if_missing(components, root, _form_step_component())
            continue
        if key == "progress":
            _append_component_if_missing(components, root, _progress_component())
            continue
        if key == "export":
            _append_component_if_missing(components, root, _export_component())
            continue
        if key == "kanban":
            _append_component_if_missing(
                components,
                root,
                _kanban_column_component("kanban_todo", "Todo", []),
                add_to_root=False,
            )
            _append_component_if_missing(
                components,
                root,
                _kanban_column_component("kanban_doing", "Doing", []),
                add_to_root=False,
            )
            _append_component_if_missing(
                components,
                root,
                _kanban_column_component("kanban_done", "Done", []),
                add_to_root=False,
            )
            _append_component_if_missing(components, root, _kanban_board_component(), root_entry="kanban_board")
            continue
        if key == "timeline":
            _append_component_if_missing(components, root, _timeline_chart_component())
            _append_component_if_missing(components, root, _timeline_table_component())
            continue
        if key == "calendar":
            _append_component_if_missing(components, root, _calendar_form_component())
            _append_component_if_missing(components, root, _calendar_table_component())
            continue
        if key == "media":
            _append_component_if_missing(components, root, _media_control_component())
            _append_component_if_missing(components, root, _media_status_component())


def _base_intro(intent: str) -> Dict[str, Any]:
    headline = (intent or "").strip() or "MetaUI Workspace"
    return {
        "id": "intro",
        "type": "text",
        "props": {
            "title": "Workspace",
            "text": headline,
            "card": True,
        },
    }


def _upload_component() -> Dict[str, Any]:
    return {
        "id": "uploader",
        "type": "file_uploader",
        "props": {
            "title": "Data Upload",
            "label": "Upload CSV/JSON/XLSX files",
            "accept": ".csv,.json,.txt,.md,.xlsx,.xls",
            "max_bytes": 8 * 1024 * 1024,
            "multiple": True,
            "card": True,
        },
    }


def _table_component() -> Dict[str, Any]:
    return {
        "id": "table_main",
        "type": "data_table",
        "props": {
            "title": "Data Preview",
            "columns": [],
            "rows": [],
            "card": True,
        },
    }


def _chart_component(chart_type: str = "bar") -> Dict[str, Any]:
    return {
        "id": "chart_main",
        "type": "chart",
        "props": {
            "title": "Visualization",
            "chart_type": chart_type,
            "labels": [],
            "values": [],
            "card": True,
        },
    }


def _form_component() -> Dict[str, Any]:
    return {
        "id": "form_main",
        "type": "form",
        "props": {
            "title": "Input Form",
            "fields": [
                {"id": "task", "type": "text", "label": "Task", "required": True},
                {"id": "owner", "type": "text", "label": "Owner"},
                {"id": "priority", "type": "select", "label": "Priority", "options": ["low", "mid", "high"]},
                {"id": "deadline", "type": "date", "label": "Deadline"},
                {"id": "notes", "type": "textarea", "label": "Notes"},
            ],
            "submit_label": "Submit",
            "card": True,
        },
    }


def _form_step_component() -> Dict[str, Any]:
    return {
        "id": "wizard_main",
        "type": "form_step",
        "props": {
            "title": "Workflow Wizard",
            "steps": [
                {
                    "title": "Step 1: Basic Info",
                    "fields": [
                        {"id": "name", "type": "text", "label": "Name", "required": True},
                        {"id": "email", "type": "text", "label": "Email"},
                    ],
                },
                {
                    "title": "Step 2: Details",
                    "fields": [
                        {"id": "goal", "type": "textarea", "label": "Goal"},
                        {"id": "budget", "type": "number", "label": "Budget", "min": 0},
                    ],
                },
                {
                    "title": "Step 3: Confirmation",
                    "fields": [
                        {"id": "confirm", "type": "checkbox", "label": "I confirm the above information"},
                    ],
                },
            ],
            "card": True,
        },
    }


def _chat_component() -> Dict[str, Any]:
    return {
        "id": "chat_main",
        "type": "chat_panel",
        "props": {
            "title": "Conversation",
            "empty_text": "No messages yet. Start by typing below.",
            "placeholder": "Type a message...",
            "send_label": "Send",
            "messages": [
                {
                    "role": "assistant",
                    "content": "Hello. I am ready to help.",
                }
            ],
            "card": True,
        },
    }


def _kanban_board_component() -> Dict[str, Any]:
    return {
        "id": "kanban_board",
        "type": "container",
        "props": {
            "title": "Kanban Board",
            "direction": "row",
            "gap": 12,
            "children": ["kanban_todo", "kanban_doing", "kanban_done"],
            "card": True,
        },
    }


def _kanban_column_component(component_id: str, title: str, rows: list[list[Any]]) -> Dict[str, Any]:
    return {
        "id": component_id,
        "type": "data_table",
        "props": {
            "title": title,
            "columns": ["task", "owner", "eta"],
            "rows": rows,
            "card": True,
        },
    }


def _timeline_chart_component() -> Dict[str, Any]:
    return {
        "id": "timeline_chart",
        "type": "chart",
        "props": {
            "title": "Timeline Trend",
            "chart_type": "line",
            "labels": ["M1", "M2", "M3", "M4"],
            "values": [1, 2, 3, 5],
            "card": True,
        },
    }


def _timeline_table_component() -> Dict[str, Any]:
    return {
        "id": "timeline_table",
        "type": "data_table",
        "props": {
            "title": "Milestones",
            "columns": ["date", "milestone", "owner", "status"],
            "rows": [
                ["2026-02-10", "Kickoff", "PM", "done"],
                ["2026-02-17", "Prototype", "Engineer", "in_progress"],
                ["2026-02-24", "Review", "Team", "planned"],
            ],
            "card": True,
        },
    }


def _calendar_table_component() -> Dict[str, Any]:
    return {
        "id": "calendar_table",
        "type": "data_table",
        "props": {
            "title": "Schedule",
            "columns": ["date", "time", "event", "owner", "location"],
            "rows": [
                ["2026-02-09", "09:00", "Standup", "Team", "Room A"],
                ["2026-02-09", "14:00", "Planning", "PM", "Room C"],
            ],
            "card": True,
        },
    }


def _calendar_form_component() -> Dict[str, Any]:
    return {
        "id": "calendar_form",
        "type": "form",
        "props": {
            "title": "Add Event",
            "fields": [
                {"id": "date", "type": "date", "label": "Date", "required": True},
                {"id": "time", "type": "text", "label": "Time", "required": True, "placeholder": "14:00"},
                {"id": "event", "type": "text", "label": "Event", "required": True},
                {"id": "owner", "type": "text", "label": "Owner"},
            ],
            "submit_label": "Add",
            "card": True,
        },
    }


def _media_control_component() -> Dict[str, Any]:
    return {
        "id": "media_control",
        "type": "form",
        "props": {
            "title": "Media Control",
            "fields": [
                {"id": "query", "type": "text", "label": "Search / URL", "required": True},
                {"id": "source", "type": "select", "label": "Source", "options": ["youtube", "spotify", "local"]},
                {"id": "autoplay", "type": "checkbox", "label": "Autoplay", "default": True},
            ],
            "submit_label": "Play",
            "card": True,
        },
    }


def _media_status_component() -> Dict[str, Any]:
    return {
        "id": "media_status",
        "type": "markdown",
        "props": {
            "title": "Now Playing",
            "text": "- status: idle\n- source: n/a\n- title: n/a",
            "card": True,
        },
    }


def _progress_component() -> Dict[str, Any]:
    return {
        "id": "progress_main",
        "type": "progress_panel",
        "props": {
            "title": "Execution Progress",
            "items": [],
            "card": True,
        },
    }


def _export_component() -> Dict[str, Any]:
    return {
        "id": "export_main",
        "type": "result_export",
        "props": {
            "title": "Export Result",
            "filename": "metaui_result",
            "data": {},
            "card": True,
        },
    }


def _default_actions(profile: _IntentProfile) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    if profile.wants_chat and profile.wants_chat_clear_action:
        actions.append(_chat_toolbar_action(action_id="chat_clear", label="Clear Messages", action_name="clear_chat"))
    if profile.wants_chat and profile.wants_chat_help_action:
        actions.append(_chat_toolbar_action(action_id="chat_help", label="Usage", action_name="show_help"))
    if profile.wants_export:
        actions.append(
            {"id": "export_now", "label": "Export", "event_type": "action", "payload": {"action": "export"}}
        )
    if profile.wants_kanban:
        actions.append(
            {"id": "new_card", "label": "New Card", "event_type": "action", "payload": {"action": "new_card"}}
        )
    if profile.wants_calendar:
        actions.append(
            {"id": "today", "label": "Today", "event_type": "action", "payload": {"action": "today"}}
        )
    return actions


def _chat_toolbar_action(*, action_id: str, label: str, action_name: str) -> Dict[str, Any]:
    effects: List[Dict[str, Any]] = []
    if action_name == "clear_chat":
        effects.append({"op": "clear_chat", "component_id": "chat_main"})
    elif action_name == "show_help":
        effects.append(
            {
                "op": "append_chat_message",
                "component_id": "chat_main",
                "value": {
                    "role": "assistant",
                    "content": "Use the input box to send messages. Use Clear to reset the conversation.",
                },
            }
        )
    return {
        "id": action_id,
        "label": label,
        "event_type": "action",
        "emit_event": True,
        "target_component_id": "chat_main",
        "payload": {"action": action_name},
        "effects": effects,
    }


def _default_state_bindings(profile: _IntentProfile) -> Dict[str, Dict[str, object]]:
    bindings: Dict[str, Dict[str, object]] = {}
    if profile.wants_table:
        bindings["table_main"] = {
            "columns": {"paths": ["currentTable.columns", "table.columns"]},
            "rows": {"paths": ["currentTable.rows", "currentTable.data", "table.rows", "table.data"]},
        }
    if profile.wants_chart:
        bindings["chart_main"] = {
            "chart_type": {
                "paths": [
                    "currentChart.chart_type",
                    "currentChart.type",
                    "currentChart.kind",
                    "chart.chart_type",
                    "chart.type",
                ]
            },
            "labels": {"paths": ["currentChart.labels", "currentChart.x", "chart.labels", "chart.x"]},
            "values": {
                "paths": [
                    "currentChart.values",
                    "currentChart.y",
                    "currentChart.data",
                    "chart.values",
                    "chart.y",
                    "chart.data",
                ]
            },
        }
    if profile.wants_timeline:
        bindings["timeline_chart"] = {
            "chart_type": {"paths": ["currentTimeline.chart_type", "timeline.chart_type"]},
            "labels": {"paths": ["currentTimeline.labels", "timeline.labels", "timeline.x"]},
            "values": {"paths": ["currentTimeline.values", "currentTimeline.y", "timeline.values", "timeline.y"]},
        }
        bindings["timeline_table"] = {
            "rows": {"paths": ["currentTimeline.events", "timeline.events", "timeline.rows"]},
            "columns": {"paths": ["currentTimeline.columns", "timeline.columns"]},
        }
    if profile.wants_kanban:
        bindings["kanban_todo"] = {
            "rows": {"paths": ["currentBoard.todo", "kanban.todo", "board.todo"]},
        }
        bindings["kanban_doing"] = {
            "rows": {"paths": ["currentBoard.doing", "kanban.doing", "board.doing"]},
        }
        bindings["kanban_done"] = {
            "rows": {"paths": ["currentBoard.done", "kanban.done", "board.done"]},
        }
    if profile.wants_calendar:
        bindings["calendar_table"] = {
            "rows": {"paths": ["currentCalendar.events", "calendar.events", "calendar.rows"]},
            "columns": {"paths": ["currentCalendar.columns", "calendar.columns"]},
        }
    if profile.wants_media:
        bindings["media_status"] = {
            "text": {"paths": ["currentMedia.text", "currentMedia.status", "media.status"]},
        }
    if profile.wants_chat:
        bindings["chat_main"] = {
            "messages": {
                "paths": [
                    "currentChat.messages",
                    "chat.messages",
                    "conversation.messages",
                    "messages",
                ]
            },
            "placeholder": {"paths": ["currentChat.placeholder", "chat.placeholder"]},
            "send_label": {"paths": ["currentChat.send_label", "chat.send_label"]},
        }
    if profile.wants_progress:
        bindings["progress_main"] = {
            "items": {"paths": ["currentProgress.items", "currentProgress", "progress.items", "progress"]},
        }
    if profile.wants_export:
        bindings["export_main"] = {
            "data": {"paths": ["currentResult.data", "result.data", "result"]},
        }
    return bindings


def build_intent_spec(intent: str, session_id: str | None) -> Dict[str, Any]:
    """
    Build a productive default MetaUI workspace based on user intent.

    The result is a complete `MetaUISpec`-compatible dict.
    """
    profile = _analyze_intent(intent)
    mode = _resolve_mode(profile)
    components: List[Dict[str, Any]] = []
    root: List[str] = []

    if mode != "chat":
        components.append(_base_intro(intent))
        root.append("intro")

    if mode == "chat":
        components.append(_chat_component())
        root.append("chat_main")
    elif mode == "kanban":
        components.extend(
            [
                _kanban_board_component(),
                _kanban_column_component(
                    "kanban_todo",
                    "Todo",
                    [["Draft requirements", "PM", "2026-02-10"], ["Collect feedback", "Analyst", "2026-02-12"]],
                ),
                _kanban_column_component(
                    "kanban_doing",
                    "Doing",
                    [["Implement API", "Engineer", "2026-02-11"]],
                ),
                _kanban_column_component(
                    "kanban_done",
                    "Done",
                    [["Scope alignment", "Team", "2026-02-08"]],
                ),
            ]
        )
        root.append("kanban_board")
        if profile.wants_form:
            components.append(_form_component())
            root.append("form_main")
    elif mode == "timeline":
        components.append(_timeline_chart_component())
        components.append(_timeline_table_component())
        root.extend(["timeline_chart", "timeline_table"])
        if profile.wants_form:
            components.append(_form_component())
            root.append("form_main")
    elif mode == "calendar":
        components.append(_calendar_form_component())
        components.append(_calendar_table_component())
        root.extend(["calendar_form", "calendar_table"])
    elif mode == "media":
        components.append(_media_control_component())
        components.append(_media_status_component())
        root.extend(["media_control", "media_status"])
        if profile.wants_progress:
            components.append(_progress_component())
            root.append("progress_main")
    elif mode == "workflow":
        components.append(_form_step_component())
        root.append("wizard_main")
    elif mode == "intake":
        components.append(_form_component())
        root.append("form_main")
    elif mode == "analytics":
        if profile.wants_upload:
            components.append(_upload_component())
            root.append("uploader")
        if profile.wants_table:
            components.append(_table_component())
            root.append("table_main")
        if profile.wants_chart:
            components.append(_chart_component(chart_type=profile.chart_type))
            root.append("chart_main")
        if profile.wants_chat:
            components.append(_chat_component())
            root.append("chat_main")
    else:
        components.append(_form_component())
        root.append("form_main")

    if profile.wants_progress and "progress_main" not in root:
        components.append(_progress_component())
        root.append("progress_main")
    if profile.wants_export and "export_main" not in root:
        components.append(_export_component())
        root.append("export_main")

    _ensure_requested_components(profile, components, root)
    _inject_chart_values(components, profile.chart_values)
    root = _reorder_root(root, profile.requested_order)

    return {
        "title": "MetaUI Workspace",
        "session_id": session_id,
        "components": components,
        "root": root,
        "theme": {"mode": profile.theme_mode} if profile.theme_mode else {},
        "actions": _default_actions(profile),
        "state_bindings": _default_state_bindings(profile),
    }


def build_scaffold_spec(intent: str, session_id: str | None) -> Dict[str, Any]:
    """Backward-compatible alias for older callers."""
    return build_intent_spec(intent=intent, session_id=session_id)
