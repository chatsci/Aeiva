"""Composed resolution layer for BrowserService."""

from __future__ import annotations

from .service_interaction_state import BrowserServiceInteractionStateMixin
from .service_scroll_guard import BrowserServiceScrollGuardMixin
from .service_target_resolution import BrowserServiceTargetResolutionMixin


class BrowserServiceResolutionMixin(
    BrowserServiceInteractionStateMixin,
    BrowserServiceTargetResolutionMixin,
    BrowserServiceScrollGuardMixin,
):
    """Composition point for target resolution and scroll guard behaviors."""
