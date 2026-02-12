from __future__ import annotations

"""Compatibility re-exports for pre-refactor runtime imports.

Runtime configuration and orchestrator lifecycle now live in
`aeiva.metaui.orchestrator`. This module remains as a thin adapter so older
imports keep working while avoiding bidirectional module coupling.
"""

from .orchestrator import (
    MetaUIEndpoint,
    MetaUIRuntimeSettings,
    configure_metaui_runtime,
    get_metaui_orchestrator,
    get_metaui_runtime_settings,
)

__all__ = [
    "MetaUIEndpoint",
    "MetaUIRuntimeSettings",
    "configure_metaui_runtime",
    "get_metaui_orchestrator",
    "get_metaui_runtime_settings",
]
