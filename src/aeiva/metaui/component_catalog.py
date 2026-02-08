from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

COMPONENT_CATALOG_VERSION = "1.0"

# A2UI-style standard catalog:
# - declarative
# - renderer-controlled
# - safe, finite component set
STANDARD_COMPONENT_CATALOG: Dict[str, Dict[str, Any]] = {
    "container": {
        "category": "layout",
        "description": "Layout container with vertical/horizontal children.",
        "props": {"direction": "column|row", "children": "string[]", "gap": "number", "title": "string"},
    },
    "tabs": {
        "category": "layout",
        "description": "Tabbed container that switches visible child groups.",
        "props": {
            "tabs": "Array<{id,label,children[]}>",
            "active_tab": "string",
            "title": "string",
            "events": "object",
            "on_change": "object",
        },
    },
    "accordion": {
        "category": "layout",
        "description": "Collapsible sections with child component groups.",
        "props": {
            "sections": "Array<{id,title,children[]}>",
            "open_section": "string",
            "title": "string",
            "events": "object",
            "on_change": "object",
        },
    },
    "divider": {
        "category": "layout",
        "description": "Visual separator line.",
        "props": {"label": "string"},
    },
    "text": {
        "category": "display",
        "description": "Plain text block.",
        "props": {"text": "string", "title": "string"},
    },
    "markdown": {
        "category": "display",
        "description": "Markdown-like text block (rendered safely as escaped text).",
        "props": {"text": "string", "title": "string"},
    },
    "badge": {
        "category": "display",
        "description": "Small status pill.",
        "props": {"text": "string", "tone": "info|success|warn|error"},
    },
    "metric_card": {
        "category": "display",
        "description": "KPI card with value and optional delta.",
        "props": {"label": "string", "value": "string|number", "delta": "string|number", "tone": "string"},
    },
    "list_view": {
        "category": "display",
        "description": "Simple item list.",
        "props": {"items": "array", "title": "string"},
    },
    "code_block": {
        "category": "display",
        "description": "Monospace code/text block.",
        "props": {"code": "string", "language": "string", "title": "string"},
    },
    "image": {
        "category": "media",
        "description": "Image display component.",
        "props": {"src": "string", "alt": "string", "width": "number", "height": "number", "fit": "string"},
    },
    "iframe": {
        "category": "media",
        "description": "Embedded frame for trusted sources.",
        "props": {"src": "string", "height": "number", "sandbox": "string"},
    },
    "chat_panel": {
        "category": "interaction",
        "description": "Chat transcript and message input.",
        "props": {
            "messages": "array",
            "placeholder": "string",
            "send_label": "string",
            "events": "object",
            "on_submit": "object",
            "emit_event": "boolean",
        },
    },
    "file_uploader": {
        "category": "input",
        "description": "File upload control.",
        "props": {
            "accept": "string",
            "multiple": "boolean",
            "max_bytes": "number",
            "label": "string",
            "events": "object",
            "on_upload": "object",
            "emit_event": "boolean",
        },
    },
    "data_table": {
        "category": "data",
        "description": "Tabular data preview.",
        "props": {"columns": "string[]", "rows": "array", "title": "string"},
    },
    "chart": {
        "category": "data",
        "description": "Bar/line chart.",
        "props": {"chart_type": "bar|line", "labels": "string[]", "values": "number[]", "title": "string"},
    },
    "form": {
        "category": "input",
        "description": "Declarative form builder.",
        "props": {
            "fields": "array",
            "submit_label": "string",
            "title": "string",
            "events": "object",
            "on_submit": "object",
            "emit_event": "boolean",
        },
    },
    "form_step": {
        "category": "input",
        "description": "Multi-step wizard form.",
        "props": {
            "steps": "array",
            "title": "string",
            "events": "object",
            "on_submit": "object",
            "on_change": "object",
            "emit_event": "boolean",
        },
    },
    "button": {
        "category": "input",
        "description": "Standalone action button.",
        "props": {
            "label": "string",
            "event_type": "string",
            "payload": "object",
            "variant": "primary|secondary",
            "effects": "object|object[]",
            "emit_event": "bool",
        },
    },
    "input": {
        "category": "input",
        "description": "Single-line input field.",
        "props": {
            "name": "string",
            "label": "string",
            "value": "string|number",
            "input_type": "string",
            "events": "object",
            "on_change": "object",
            "on_submit": "object",
            "emit_event": "boolean",
        },
    },
    "textarea": {
        "category": "input",
        "description": "Multi-line input field.",
        "props": {
            "name": "string",
            "label": "string",
            "value": "string",
            "rows": "number",
            "events": "object",
            "on_change": "object",
            "emit_event": "boolean",
        },
    },
    "select": {
        "category": "input",
        "description": "Select dropdown.",
        "props": {
            "name": "string",
            "label": "string",
            "options": "array",
            "value": "string",
            "events": "object",
            "on_change": "object",
            "emit_event": "boolean",
        },
    },
    "checkbox": {
        "category": "input",
        "description": "Boolean toggle.",
        "props": {
            "name": "string",
            "label": "string",
            "checked": "boolean",
            "events": "object",
            "on_change": "object",
            "emit_event": "boolean",
        },
    },
    "radio_group": {
        "category": "input",
        "description": "Single-choice option group.",
        "props": {
            "name": "string",
            "label": "string",
            "options": "array",
            "value": "string",
            "events": "object",
            "on_change": "object",
            "emit_event": "boolean",
        },
    },
    "slider": {
        "category": "input",
        "description": "Numeric range slider.",
        "props": {
            "name": "string",
            "label": "string",
            "value": "number",
            "min": "number",
            "max": "number",
            "events": "object",
            "on_change": "object",
            "emit_event": "boolean",
        },
    },
    "progress_panel": {
        "category": "feedback",
        "description": "Progress items display.",
        "props": {"items": "Array<{label,value}>", "title": "string"},
    },
    "result_export": {
        "category": "feedback",
        "description": "Export controls for result payloads.",
        "props": {
            "filename": "string",
            "data": "object",
            "title": "string",
            "events": "object",
            "on_export": "object",
            "emit_event": "boolean",
        },
    },
}

STANDARD_COMPONENT_ALIASES: Dict[str, str] = {
    "Row": "container",
    "Column": "container",
    "Card": "container",
    "Modal": "container",
    "TextField": "input",
    "ChoicePicker": "select",
    "DateTimeInput": "input",
    "Icon": "badge",
    "Video": "iframe",
    "AudioPlayer": "iframe",
    "CheckBox": "checkbox",
    "RadioGroup": "radio_group",
    "List": "list_view",
}


def supported_component_types() -> set[str]:
    return set(STANDARD_COMPONENT_CATALOG.keys())


def get_component_catalog() -> Dict[str, Any]:
    return {
        "version": COMPONENT_CATALOG_VERSION,
        "components": deepcopy(STANDARD_COMPONENT_CATALOG),
        "aliases": deepcopy(STANDARD_COMPONENT_ALIASES),
    }
