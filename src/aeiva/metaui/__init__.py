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
from .session import MetaUIPhase, MetaUISession
from .component_catalog import get_component_catalog, supported_component_types
from .event_bridge import (
    MetaUIEventBridge,
    MetaUIEventBridgeConfig,
    build_metaui_event_prompt,
    parse_metaui_event_bridge_config,
    start_metaui_event_bridge,
)

__all__ = [
    "MetaUICommand",
    "MetaUIComponent",
    "MetaUIEndpoint",
    "MetaUIEvent",
    "MetaUIOrchestrator",
    "MetaUIPhase",
    "MetaUISession",
    "MetaUISpec",
    "build_metaui_event_prompt",
    "get_component_catalog",
    "MetaUIEventBridge",
    "MetaUIEventBridgeConfig",
    "configure_metaui_runtime",
    "get_metaui_orchestrator",
    "get_metaui_runtime_settings",
    "parse_metaui_event_bridge_config",
    "start_metaui_event_bridge",
    "new_command_id",
    "new_event_id",
    "new_ui_id",
    "supported_component_types",
]
