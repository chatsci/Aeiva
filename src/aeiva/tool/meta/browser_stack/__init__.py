"""
Browser stack utilities.

This package holds browser-adjacent infrastructure that should stay separate
from the large browser service/runtime modules (security policies, shared
helpers, and future refactors).
"""

from .runtime import BrowserSessionManager, BrowserRuntime, PlaywrightRuntime, DEFAULT_TIMEOUT_MS
from .security import BrowserSecurityPolicy
from .service import BrowserService, get_browser_service, set_browser_service

__all__ = [
    "BrowserService",
    "BrowserRuntime",
    "BrowserSecurityPolicy",
    "BrowserSessionManager",
    "DEFAULT_TIMEOUT_MS",
    "PlaywrightRuntime",
    "get_browser_service",
    "set_browser_service",
]
