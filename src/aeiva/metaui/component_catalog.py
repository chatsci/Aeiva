from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from .interaction_contract import get_interaction_contract_snapshot

COMPONENT_CATALOG_VERSION = "0.10"

# Strict A2UI-native component catalog (no legacy aliases).
STANDARD_COMPONENT_CATALOG: Dict[str, Dict[str, Any]] = {
    "Text": {
        "category": "display",
        "description": "Text label or paragraph.",
        "props": {"text": "DynamicString", "variant": "h1|h2|h3|h4|h5|caption|body"},
    },
    "Image": {
        "category": "display",
        "description": "Image content.",
        "props": {
            "url": "DynamicString",
            "fit": "contain|cover|fill|none|scale-down",
            "variant": "icon|avatar|smallFeature|mediumFeature|largeFeature|header",
        },
    },
    "Icon": {
        "category": "display",
        "description": "Icon glyph.",
        "props": {"name": "DynamicString"},
    },
    "Video": {
        "category": "media",
        "description": "Video player.",
        "props": {"url": "DynamicString"},
    },
    "AudioPlayer": {
        "category": "media",
        "description": "Audio player.",
        "props": {"url": "DynamicString", "description": "DynamicString"},
    },
    "Row": {
        "category": "layout",
        "description": "Horizontal layout container.",
        "props": {"children": "ChildList", "justify": "enum", "align": "enum", "weight": "number"},
    },
    "Column": {
        "category": "layout",
        "description": "Vertical layout container.",
        "props": {"children": "ChildList", "justify": "enum", "align": "enum", "weight": "number"},
    },
    "List": {
        "category": "layout",
        "description": "List layout with static children or template binding.",
        "props": {"children": "ChildList", "direction": "vertical|horizontal", "align": "enum"},
    },
    "Card": {
        "category": "layout",
        "description": "Card shell with one child.",
        "props": {"child": "ComponentId", "weight": "number"},
    },
    "Tabs": {
        "category": "layout",
        "description": "Tabs container.",
        "props": {"tabs": "Array<{title,child}>", "weight": "number"},
    },
    "Modal": {
        "category": "layout",
        "description": "Modal with trigger and content component ids.",
        "props": {"trigger": "ComponentId", "content": "ComponentId"},
    },
    "Divider": {
        "category": "layout",
        "description": "Section divider line.",
        "props": {"axis": "horizontal|vertical"},
    },
    "Button": {
        "category": "input",
        "description": "Action button.",
        "props": {
            "child": "ComponentId",
            "variant": "primary|borderless",
            "action": "Action",
            "checks": "CheckRule[]",
        },
    },
    "TextField": {
        "category": "input",
        "description": "Editable text/number field.",
        "props": {
            "label": "DynamicString",
            "value": "DynamicString",
            "variant": "longText|number|shortText|obscured",
            "checks": "CheckRule[]",
        },
    },
    "CheckBox": {
        "category": "input",
        "description": "Boolean checkbox.",
        "props": {"label": "DynamicString", "value": "DynamicBoolean", "checks": "CheckRule[]"},
    },
    "ChoicePicker": {
        "category": "input",
        "description": "Single/multi select picker.",
        "props": {
            "label": "DynamicString",
            "variant": "multipleSelection|mutuallyExclusive",
            "options": "Array<{label,value}>",
            "value": "DynamicStringList",
            "checks": "CheckRule[]",
        },
    },
    "Slider": {
        "category": "input",
        "description": "Numeric slider.",
        "props": {
            "label": "DynamicString",
            "value": "DynamicNumber",
            "min": "DynamicNumber",
            "max": "DynamicNumber",
            "checks": "CheckRule[]",
        },
    },
    "DateTimeInput": {
        "category": "input",
        "description": "Date/time selector.",
        "props": {
            "value": "DynamicString",
            "label": "DynamicString",
            "enableDate": "boolean",
            "enableTime": "boolean",
            "min": "DynamicString",
            "max": "DynamicString",
            "checks": "CheckRule[]",
        },
    },
}


def supported_component_types() -> set[str]:
    return set(STANDARD_COMPONENT_CATALOG.keys())


def get_component_catalog() -> Dict[str, Any]:
    return {
        "version": COMPONENT_CATALOG_VERSION,
        "components": deepcopy(STANDARD_COMPONENT_CATALOG),
        "interaction_contract": get_interaction_contract_snapshot(),
    }
