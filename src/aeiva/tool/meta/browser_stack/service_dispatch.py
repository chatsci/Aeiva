"""Composed dispatch layer for BrowserService."""

from __future__ import annotations

from .service_dispatch_core import BrowserServiceDispatchCoreMixin
from .service_dispatch_interaction import BrowserServiceDispatchInteractionMixin


class BrowserServiceDispatchMixin(
    BrowserServiceDispatchCoreMixin,
    BrowserServiceDispatchInteractionMixin,
):
    """Composition point for operation-dispatch branches."""

