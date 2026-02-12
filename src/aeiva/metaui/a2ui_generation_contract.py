from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from .component_catalog import get_component_catalog
from .interaction_contract import get_interaction_contract_snapshot


_A2UI_PROMPT_GENERATE_VALIDATE_LOOP: List[Dict[str, str]] = [
    {
        "step": "prompt",
        "description": (
            "Provide desired UI objective, protocol schema, component catalog, "
            "and a small set of valid examples."
        ),
    },
    {
        "step": "generate",
        "description": (
            "Generate explicit UI structure and interaction actions as strict JSON data "
            "without free-form code."
        ),
    },
    {
        "step": "validate",
        "description": (
            "Validate generated spec against schema/contract. If invalid, feed structured "
            "validation errors back to the model and retry."
        ),
    },
]

_A2UI_REQUIRED_RULES_TEXT = (
    "REQUIRED PROPERTIES: you MUST include all required fields for every component; "
    "for Text provide props.text; for Image provide props.url; "
    "for Button provide props.action; for TextField/CheckBox/ChoicePicker/Slider/DateTimeInput provide labels or required value fields; "
    "only use canonical catalog component names and declared function calls."
)

_A2UI_UI_RULES: List[str] = [
    "AI defines UI structure and interaction logic explicitly in spec JSON.",
    "MetaUI runtime only validates, renders, and relays interaction events.",
    "No intent inference, no scaffold synthesis, no fallback UI injection.",
    "All interactive behavior must be declared via Action object (event or functionCall).",
    "Interactive specs must include at least one actionable control (Button action or value-bound input).",
    "Input controls must use props.value data binding object with non-empty `path`.",
    "Unknown component types or function calls are rejected deterministically.",
]

_A2UI_FUNCTIONAL_UI_CHECKLIST: List[str] = [
    "Every Button must define props.action with either event or functionCall.",
    "Every input component (TextField, CheckBox, ChoicePicker, Slider, DateTimeInput) should bind to state via props.value path.",
    "Events must be named explicitly and carry deterministic context payload paths.",
    "Specs must remain strictly canonical: no aliases, no inferred defaults, no undeclared behaviors.",
]

_A2UI_VALIDATION_ERROR_FORMAT: Dict[str, Any] = {
    "code": "VALIDATION_FAILED",
    "path": "/json/pointer/path",
    "message": "Human-readable one-line validation failure.",
}

_A2UI_INTERACTION_FIX_GUIDE: Dict[str, Any] = {
    "button_action": {
        "event": {"name": "ui_submit", "context": {"path": "/form"}},
        "functionCall": {
            "call": "setPath",
            "args": {"path": "/draft", "value": ""},
            "returnType": "void",
        },
    },
    "value_binding_example": {"path": "/state/field"},
    "required_notes": [
        "Button.props.action is required in interactive mode.",
        "TextField/CheckBox/ChoicePicker/Slider/DateTimeInput should bind props.value.path.",
        "Use canonical component names and declared function calls only.",
    ],
}

_A2UI_EXAMPLE_SPECS: List[Dict[str, Any]] = [
    {
        "name": "chat_ui",
        "spec": {
            "title": "Dialogue Workspace",
            "interaction_mode": "interactive",
            "components": [
                {"id": "title", "type": "Text", "props": {"text": "Chat", "variant": "h3"}},
                {"id": "history", "type": "List", "props": {"children": {"componentId": "msg_card", "path": "/messages"}}},
                {"id": "msg_card", "type": "Card", "props": {"child": "msg_text"}},
                {"id": "msg_text", "type": "Text", "props": {"text": {"path": "item.text"}}},
                {"id": "draft", "type": "TextField", "props": {"label": "Message", "value": {"path": "/draft"}, "variant": "shortText"}},
                {"id": "send_label", "type": "Text", "props": {"text": "Send"}},
                {
                    "id": "send_btn",
                    "type": "Button",
                    "props": {
                        "child": "send_label",
                        "variant": "primary",
                        "action": {
                            "functionCall": {
                                "call": "runSequence",
                                "args": {
                                    "steps": [
                                        {
                                            "call": "appendState",
                                            "args": {
                                                "path": "/messages",
                                                "value": {"role": "user", "text": {"path": "/draft"}},
                                            },
                                        },
                                        {"call": "setState", "args": {"path": "/draft", "value": ""}},
                                    ]
                                },
                            }
                        },
                    },
                },
                {"id": "clear_label", "type": "Text", "props": {"text": "Clear"}},
                {
                    "id": "clear_btn",
                    "type": "Button",
                    "props": {
                        "child": "clear_label",
                        "action": {
                            "functionCall": {
                                "call": "runSequence",
                                "args": {
                                    "steps": [
                                        {"call": "setState", "args": {"path": "/messages", "value": []}},
                                        {"call": "setState", "args": {"path": "/draft", "value": ""}},
                                    ]
                                },
                            }
                        },
                    },
                },
                {"id": "row", "type": "Row", "props": {"children": ["draft", "send_btn", "clear_btn"], "align": "center"}},
                {"id": "root", "type": "Column", "props": {"children": ["title", "history", "row"]}},
            ],
            "root": ["root"],
            "state": {"messages": [], "draft": ""},
        },
    },
    {
        "name": "form_ui",
        "spec": {
            "title": "Employee Onboarding",
            "interaction_mode": "interactive",
            "components": [
                {"id": "name", "type": "TextField", "props": {"label": "Name", "value": {"path": "/form/name"}}},
                {"id": "dept", "type": "TextField", "props": {"label": "Department", "value": {"path": "/form/department"}}},
                {"id": "submit_label", "type": "Text", "props": {"text": "Submit"}},
                {
                    "id": "submit",
                    "type": "Button",
                    "props": {
                        "child": "submit_label",
                        "action": {"functionCall": {"call": "setState", "args": {"path": "/submitted", "value": True}}},
                    },
                },
                {"id": "reset_label", "type": "Text", "props": {"text": "Reset"}},
                {
                    "id": "reset",
                    "type": "Button",
                    "props": {
                        "child": "reset_label",
                        "action": {
                            "functionCall": {
                                "call": "runSequence",
                                "args": {
                                    "steps": [
                                        {"call": "setState", "args": {"path": "/form/name", "value": ""}},
                                        {"call": "setState", "args": {"path": "/form/department", "value": ""}},
                                        {"call": "setState", "args": {"path": "/submitted", "value": False}},
                                    ]
                                },
                            }
                        },
                    },
                },
                {"id": "root", "type": "Column", "props": {"children": ["name", "dept", "submit", "reset"]}},
            ],
            "root": ["root"],
            "state": {"form": {"name": "", "department": ""}, "submitted": False},
        },
    },
]

_PRESET_SPECS: Dict[str, Dict[str, Any]] = {
    str(entry.get("name") or "").strip(): deepcopy(entry.get("spec") or {})
    for entry in _A2UI_EXAMPLE_SPECS
    if isinstance(entry, dict) and str(entry.get("name") or "").strip()
}

def get_interaction_fix_guide() -> Dict[str, Any]:
    """Return compact canonical snippets for repairing invalid interactive specs."""
    return deepcopy(_A2UI_INTERACTION_FIX_GUIDE)


def get_available_presets() -> List[str]:
    """Return stable preset names that map to canonical strict example specs."""
    return sorted(_PRESET_SPECS.keys())


def resolve_preset_spec(
    preset_name: str,
    *,
    title: str | None = None,
) -> Dict[str, Any] | None:
    """Resolve a preset name into a strict explicit spec payload."""
    token = str(preset_name or "").strip()
    if not token:
        return None
    base = _PRESET_SPECS.get(token)
    if base is None:
        return None
    resolved = deepcopy(base)
    if title is not None:
        title_value = str(title).strip()
        if title_value:
            resolved["title"] = title_value
    return resolved


def get_a2ui_generation_contract() -> Dict[str, Any]:
    """Return a strict, prompt-ready generation contract aligned with A2UI method."""
    catalog = get_component_catalog()
    interaction_contract = get_interaction_contract_snapshot()
    components = sorted((catalog.get("components") or {}).keys())
    function_catalog = interaction_contract.get("function_catalog") or {}
    return {
        "policy": "strict",
        "loop": deepcopy(_A2UI_PROMPT_GENERATE_VALIDATE_LOOP),
        "rules_text": _A2UI_REQUIRED_RULES_TEXT,
        "rules": list(_A2UI_UI_RULES),
        "functional_ui_checklist": list(_A2UI_FUNCTIONAL_UI_CHECKLIST),
        "presets": get_available_presets(),
        "interaction_fix_guide": get_interaction_fix_guide(),
        "canonical_components": components,
        "function_catalog": deepcopy(function_catalog),
        "validation_error_format": deepcopy(_A2UI_VALIDATION_ERROR_FORMAT),
        "examples": deepcopy(_A2UI_EXAMPLE_SPECS),
    }
