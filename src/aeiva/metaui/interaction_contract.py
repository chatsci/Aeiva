from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Final, Tuple

from .function_catalog import (
    get_function_catalog_snapshot,
    get_standard_function_catalog_snapshot,
)

# Strict A2UI interaction contract.
#
# MetaUI runtime follows one channel only:
# - UI structure is defined by AI using A2UI components.
# - interactive behavior is defined by A2UI Action objects.
# - runtime does not infer intent heuristically.

COMPONENT_SUPPORTED_EVENTS: Final[Dict[str, Tuple[str, ...]]] = {
    # Button actions are the primary server round-trip trigger in A2UI.
    "Button": ("click",),
    # The following components can produce local UI interaction events.
    "TextField": ("change", "submit"),
    "CheckBox": ("change",),
    "ChoicePicker": ("change",),
    "Slider": ("change",),
    "DateTimeInput": ("change",),
    "Tabs": ("change",),
    "Modal": ("open", "close"),
}

ACTION_VARIANTS: Final[Tuple[str, ...]] = ("event", "functionCall")
FUNCTION_CALL_RETURN_TYPES: Final[Tuple[str, ...]] = (
    "string",
    "number",
    "boolean",
    "array",
    "object",
    "any",
    "void",
)
VALUE_PATH_BINDING_COMPONENTS: Final[Tuple[str, ...]] = (
    "TextField",
    "CheckBox",
    "ChoicePicker",
    "Slider",
    "DateTimeInput",
)


def get_interaction_contract_snapshot() -> Dict[str, Any]:
    full_catalog = get_function_catalog_snapshot()
    return {
        "component_supported_events": deepcopy(COMPONENT_SUPPORTED_EVENTS),
        "action_variants": list(ACTION_VARIANTS),
        "function_call_return_types": list(FUNCTION_CALL_RETURN_TYPES),
        "standard_functions": get_standard_function_catalog_snapshot(),
        "function_catalog": full_catalog,
        "interactive_requirements": {
            "requires_actionable_component": True,
            "actionable_components": [
                "Button",
                *VALUE_PATH_BINDING_COMPONENTS,
            ],
            "value_path_binding_components": list(VALUE_PATH_BINDING_COMPONENTS),
            "button_requires_action": True,
        },
    }
