"""
AEIVA Tool System.

Provides a unified interface for tool definitions and execution.

Structure:
    - meta/: Universal primitives (Tier 1)
    - core/: Frequently used operations (Tier 2)
    - decorator: @tool decorator for defining tools
    - capability: Capability enum for tool permissions
    - registry: Auto-discovery and management
"""

from .decorator import tool, ToolMetadata, ToolParam
from .capability import Capability
from .registry import ToolRegistry, get_registry, get_tool, get_schemas

__all__ = [
    # Decorator
    "tool",
    "ToolMetadata",
    "ToolParam",
    # Capability
    "Capability",
    # Registry
    "ToolRegistry",
    "get_registry",
    "get_tool",
    "get_schemas",
]
