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

    def _clear_profile_interaction_state(self, profile: str) -> None:
        self._clear_field_target_lock(profile)
        self._clear_scroll_guard(profile)
