"""
Tool Registry: Auto-discovery and management of tools.

Discovers tools from meta/ and core/ directories, provides
unified access to schemas and execution.

Usage:
    from aeiva.tool.registry import ToolRegistry

    registry = ToolRegistry()
    registry.discover()

    # Get all tool schemas for LLM
    schemas = registry.get_schemas()

    # Execute a tool
    result = await registry.execute("shell", command="ls -la")
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .capability import Capability
from .decorator import ToolMetadata

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all tools.

    Automatically discovers tools from:
    - meta/  (Tier 1: universal primitives)
    - core/  (Tier 2: frequently used)

    Provides:
    - Schema access for LLM function calling
    - Unified execution interface
    - Capability querying
    """

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._tool_tiers: Dict[str, str] = {}  # tool_name -> tier (meta/core)
        self._discovered = False

    def discover(self, base_path: Path = None) -> None:
        """
        Discover all tools from meta/ and core/ directories.

        Args:
            base_path: Base path to search (defaults to this module's directory)
        """
        if base_path is None:
            base_path = Path(__file__).parent

        # Discover from meta/ and core/
        for tier in ("meta", "core"):
            tier_path = base_path / tier
            if tier_path.exists():
                self._discover_tier(tier_path, tier)

        self._discovered = True
        logger.info(f"Discovered {len(self._tools)} tools: {list(self._tools.keys())}")

    def _discover_tier(self, tier_path: Path, tier_name: str) -> None:
        """Discover tools from a single tier directory."""
        for file_path in tier_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            module_name = file_path.stem
            try:
                # Import the module
                full_module = f"aeiva.tool.{tier_name}.{module_name}"
                module = importlib.import_module(full_module)

                # Find decorated functions
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, "metadata"):
                        metadata: ToolMetadata = attr.metadata
                        self._tools[metadata.name] = metadata
                        self._tool_tiers[metadata.name] = tier_name
                        logger.debug(f"Registered tool: {metadata.name} from {tier_name}/")

            except Exception as e:
                logger.warning(f"Failed to load tool from {file_path}: {e}")

    def register(self, func: Callable) -> None:
        """
        Manually register a decorated tool function.

        Args:
            func: A function decorated with @tool
        """
        if not hasattr(func, "metadata"):
            raise ValueError(f"Function {func.__name__} is not decorated with @tool")

        metadata: ToolMetadata = func.metadata
        self._tools[metadata.name] = metadata

    def get(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name."""
        return self._tools.get(name)

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for a single tool."""
        tool = self._tools.get(name)
        return tool.to_json_schema() if tool else None

    def get_schemas(self, names: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get JSON schemas for multiple tools.

        Args:
            names: List of tool names (None = all tools)

        Returns:
            List of JSON schemas in OpenAI function calling format
        """
        if names is None:
            return [t.to_json_schema() for t in self._tools.values()]

        schemas = []
        for name in names:
            tool = self._tools.get(name)
            if tool:
                schemas.append(tool.to_json_schema())
        return schemas

    def get_by_capability(self, capability: Capability) -> List[ToolMetadata]:
        """Get all tools that have a specific capability."""
        return [t for t in self._tools.values() if capability in t.capabilities]

    def get_capabilities(self, name: str) -> Set[Capability]:
        """Get capabilities required by a tool."""
        tool = self._tools.get(name)
        return tool.capabilities if tool else set()

    async def execute(self, name: str, **kwargs) -> Any:
        """
        Execute a tool by name.

        Args:
            name: Tool name
            **kwargs: Tool parameters

        Returns:
            Tool execution result

        Raises:
            KeyError: If tool not found
        """
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Tool not found: {name}")

        if _tool_router is not None:
            try:
                routed = await _tool_router.execute(name, kwargs)
                if routed is not None:
                    return routed
            except Exception:
                raise

        return await tool.execute(**kwargs)

    def execute_sync(self, name: str, **kwargs) -> Any:
        """
        Execute a tool synchronously.

        Args:
            name: Tool name
            **kwargs: Tool parameters

        Returns:
            Tool execution result
        """
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"Tool not found: {name}")

        if _tool_router is not None:
            try:
                routed = _tool_router.execute_sync(name, kwargs)
                if routed is not None:
                    return routed
            except Exception:
                raise

        return tool.execute_sync(**kwargs)

    @property
    def tool_names(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    @property
    def meta_tools(self) -> List[str]:
        """List meta tool names (Tier 1: universal primitives)."""
        return [name for name, tier in self._tool_tiers.items() if tier == "meta"]

    @property
    def core_tools(self) -> List[str]:
        """List core tool names (Tier 2: frequently used)."""
        return [name for name, tier in self._tool_tiers.items() if tier == "core"]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools.values())


# Global registry instance
_global_registry: Optional[ToolRegistry] = None
_tool_router: Optional[Any] = None


def set_tool_router(router: Any) -> None:
    """Attach a tool router for remote host execution."""
    global _tool_router
    _tool_router = router


def get_registry() -> ToolRegistry:
    """Get the global tool registry, discovering tools if needed."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _global_registry.discover()
    return _global_registry


def get_tool(name: str) -> Optional[ToolMetadata]:
    """Get a tool by name from the global registry."""
    return get_registry().get(name)


def get_schemas(names: List[str] = None) -> List[Dict[str, Any]]:
    """Get tool schemas from the global registry."""
    return get_registry().get_schemas(names)
