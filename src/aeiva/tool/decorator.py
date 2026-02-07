"""
Tool Decorator: Single source of truth for tool definitions.

Automatically generates:
- JSON schema (OpenAI function calling format)
- Pydantic models for validation
- Documentation

Usage:
    from aeiva.tool.decorator import tool
    from aeiva.tool.capability import Capability

    @tool(
        description="Execute a shell command",
        capabilities=[Capability.SHELL],
    )
    async def shell(
        command: str,
        timeout: int = 30,
    ) -> dict:
        '''Execute command and return output.'''
        ...

The decorator extracts schema from:
- Function name → tool name
- Type hints → parameter types
- Default values → optional parameters
- Docstring → additional documentation
"""

import asyncio
import inspect
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Set,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from .capability import Capability


# ═══════════════════════════════════════════════════════════════════
# TYPE TO JSON SCHEMA MAPPING
# ═══════════════════════════════════════════════════════════════════

def python_type_to_json_schema(py_type: Type) -> Dict[str, Any]:
    """Convert Python type hint to JSON schema type."""
    origin = get_origin(py_type)
    args = get_args(py_type)

    # Handle Optional[X] → {"type": X, "nullable": true}
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            schema = python_type_to_json_schema(non_none[0])
            return schema
        return {"type": "string"}  # Fallback for complex unions

    # Handle List[X]
    if origin is list:
        item_type = args[0] if args else Any
        return {
            "type": "array",
            "items": python_type_to_json_schema(item_type),
        }

    # Handle Dict[K, V]
    if origin is dict:
        return {"type": "object"}

    # Primitive types
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        bytes: {"type": "string", "format": "binary"},
        type(None): {"type": "null"},
        Any: {"type": "string"},  # Fallback
    }

    return type_map.get(py_type, {"type": "string"})


# ═══════════════════════════════════════════════════════════════════
# TOOL METADATA
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ToolParam:
    """Metadata for a single tool parameter."""
    name: str
    type: Type
    description: str
    required: bool
    default: Any = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema property."""
        schema = python_type_to_json_schema(self.type)
        schema["description"] = self.description
        return schema


@dataclass
class ToolMetadata:
    """Complete metadata for a tool, extracted from decorated function."""
    name: str
    description: str
    capabilities: Set[Capability]
    parameters: List[ToolParam]
    return_type: Type
    is_async: bool
    func: Callable

    def to_json_schema(self) -> Dict[str, Any]:
        """Generate OpenAI function calling format schema."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        if self.is_async:
            return await self.func(**kwargs)
        else:
            return self.func(**kwargs)

    def execute_sync(self, **kwargs) -> Any:
        """Execute the tool synchronously."""
        if self.is_async:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(self.func(**kwargs))
            raise RuntimeError("Cannot call execute_sync from async context")
        else:
            return self.func(**kwargs)


# ═══════════════════════════════════════════════════════════════════
# PARAMETER DESCRIPTION EXTRACTION
# ═══════════════════════════════════════════════════════════════════

def extract_param_descriptions(func: Callable) -> Dict[str, str]:
    """
    Extract parameter descriptions from docstring.

    Supports formats:
        Args:
            param_name: Description here.
            param_name (type): Description here.
    """
    doc = inspect.getdoc(func) or ""
    descriptions = {}

    in_args_section = False
    current_param = None
    current_desc = []

    for line in doc.split('\n'):
        stripped = line.strip()

        if stripped.lower() in ('args:', 'arguments:', 'parameters:'):
            in_args_section = True
            continue

        if stripped.lower() in ('returns:', 'return:', 'raises:', 'example:', 'examples:'):
            in_args_section = False
            if current_param:
                descriptions[current_param] = ' '.join(current_desc).strip()
            current_param = None
            continue

        if in_args_section and stripped:
            # Check if this is a new parameter line
            if ':' in stripped and not stripped.startswith(' '):
                # Save previous parameter
                if current_param:
                    descriptions[current_param] = ' '.join(current_desc).strip()

                # Parse new parameter
                parts = stripped.split(':', 1)
                param_part = parts[0].strip()
                desc_part = parts[1].strip() if len(parts) > 1 else ""

                # Handle "param_name (type)" format
                if '(' in param_part:
                    param_part = param_part.split('(')[0].strip()

                current_param = param_part
                current_desc = [desc_part] if desc_part else []
            elif current_param:
                # Continuation of previous description
                current_desc.append(stripped)

    # Save last parameter
    if current_param:
        descriptions[current_param] = ' '.join(current_desc).strip()

    return descriptions


# ═══════════════════════════════════════════════════════════════════
# THE DECORATOR
# ═══════════════════════════════════════════════════════════════════

def tool(
    description: str,
    capabilities: List[Capability] = None,
    name: str = None,
) -> Callable:
    """
    Decorator that converts a function into a tool with auto-generated schema.

    Args:
        description: Human-readable description of what the tool does.
        capabilities: List of Capability enums this tool requires.
        name: Override tool name (defaults to function name).

    Returns:
        Decorated function with .metadata attribute containing ToolMetadata.

    Example:
        @tool(
            description="Search the web",
            capabilities=[Capability.NETWORK],
        )
        async def web_search(query: str, max_results: int = 10) -> dict:
            '''
            Search the web for the given query.

            Args:
                query: The search query string.
                max_results: Maximum number of results to return.

            Returns:
                Dictionary with search results.
            '''
            ...
    """
    capabilities = capabilities or [Capability.NONE]

    def decorator(func: Callable) -> Callable:
        # Get function signature
        sig = inspect.signature(func)
        type_hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
        param_descriptions = extract_param_descriptions(func)

        # Build parameter list
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls'):
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            param_type = type_hints.get(param_name, str)
            has_default = param.default is not inspect.Parameter.empty
            default = param.default if has_default else None

            # Get description from docstring or use placeholder
            desc = param_descriptions.get(param_name, f"The {param_name} parameter")

            parameters.append(ToolParam(
                name=param_name,
                type=param_type,
                description=desc,
                required=not has_default,
                default=default,
            ))

        # Get return type
        return_type = type_hints.get('return', Any)

        # Create metadata
        metadata = ToolMetadata(
            name=name or func.__name__,
            description=description,
            capabilities=set(capabilities),
            parameters=parameters,
            return_type=return_type,
            is_async=asyncio.iscoroutinefunction(func),
            func=func,
        )

        # Attach metadata to function
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper = async_wrapper if metadata.is_async else sync_wrapper
        wrapper.metadata = metadata
        wrapper.schema = metadata.to_json_schema()
        wrapper.capabilities = metadata.capabilities

        return wrapper

    return decorator
