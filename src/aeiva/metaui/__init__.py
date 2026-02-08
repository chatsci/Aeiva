"""
MetaUI: channel-agnostic desktop UI orchestration for AEIVA.
"""

from .protocol import (
    MetaUICommand,
    MetaUIComponent,
    MetaUIEvent,
    MetaUISpec,
    new_command_id,
    new_event_id,
    new_ui_id,
)
from .orchestrator import MetaUIEndpoint, MetaUIOrchestrator, get_metaui_orchestrator
from .orchestrator import configure_metaui_runtime, get_metaui_runtime_settings
from .intent_spec import (
    build_intent_spec,
    build_scaffold_spec,
    intent_has_component_signals,
)
from .session import MetaUIPhase, MetaUISession
from .component_catalog import get_component_catalog, supported_component_types

__all__ = [
    "MetaUICommand",
    "MetaUIComponent",
    "MetaUIEndpoint",
    "MetaUIEvent",
    "MetaUIOrchestrator",
    "MetaUIPhase",
    "MetaUISession",
    "MetaUISpec",
    "build_intent_spec",
    "build_scaffold_spec",
    "get_component_catalog",
    "intent_has_component_signals",
    "configure_metaui_runtime",
    "get_metaui_orchestrator",
    "get_metaui_runtime_settings",
    "new_command_id",
    "new_event_id",
    "new_ui_id",
    "supported_component_types",
]
