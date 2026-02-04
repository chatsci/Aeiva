"""
Action: An executable atomic unit with Tool integration.

An Action is a Step that can be executed by connecting to a Tool.
It manages execution state and captures results.

Hierarchy:
    Step → Task (visualizable, for planning)
    Step → Action (executable, with Tool)

Usage:
    action = Action(
        name="get_weather",
        params={"city": "Seattle"},
        description="Fetch weather data"
    )
    result = await action.execute()
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from aeiva.action.step import Step, generate_step_id
from aeiva.action.status import Status

if TYPE_CHECKING:
    from aeiva.tool.decorator import ToolMetadata

logger = logging.getLogger(__name__)


@dataclass
class Action(Step):
    """
    An executable unit of work with Tool integration.

    Actions connect to Tools for execution. When executed, the Action:
    1. Marks status as EXECUTING
    2. Calls the Tool with params
    3. Captures the result
    4. Marks status as SUCCESS or FAIL

    Attributes:
        tool: Optional Tool instance for execution
              If not provided, will be resolved by name during execution

    Example:
        action = Action(
            name="search_web",
            params={"query": "Python dataclasses"},
            description="Search the web for Python dataclass info"
        )

        # Execute with auto-resolved tool
        result = await action.execute()

        # Or provide explicit tool
        result = await action.execute(tool=my_search_tool)
    """

    tool: Optional["ToolMetadata"] = field(default=None, repr=False)

    async def execute(
        self,
        params: Optional[Dict[str, Any]] = None,
        tool: Optional["ToolMetadata"] = None
    ) -> Any:
        """
        Execute the action using the tool registry or bound tool.

        Args:
            params: Override params (uses self.params if not provided)
            tool: Override tool metadata (uses self.tool or resolves by name)

        Returns:
            Result from tool execution

        Raises:
            ValueError: If no tool available
            RuntimeError: If execution fails
        """
        from aeiva.tool.registry import get_registry

        # Resolve params
        execution_params = params if params is not None else self.params

        # Execute
        self.start()
        logger.debug(f"Executing action '{self.id}' with tool '{self.name}'")

        try:
            # Try registry first (new system)
            registry = get_registry()
            if self.name in registry:
                result = await registry.execute(self.name, **execution_params)
            elif tool or self.tool:
                # Use bound tool metadata
                execution_tool = tool or self.tool
                result = await execution_tool.execute(**execution_params)
            else:
                raise ValueError(
                    f"Action '{self.id}' has no tool for execution. "
                    f"Tool '{self.name}' not found in registry."
                )

            self.succeed(result)
            logger.debug(f"Action '{self.id}' succeeded")
            return result

        except Exception as e:
            self.fail(e)
            logger.error(f"Action '{self.id}' failed: {e}")
            raise RuntimeError(f"Action '{self.id}' failed: {e}") from e

    def bind_tool(self, tool: "ToolMetadata") -> "Action":
        """
        Bind a tool to this action.

        Args:
            tool: Tool instance to bind

        Returns:
            Self for chaining
        """
        self.tool = tool
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = super().to_dict()
        data["has_tool"] = self.tool is not None
        if self.result is not None and self.is_finished:
            # Only include serializable results
            try:
                data["result"] = str(self.result)
            except Exception:
                data["result"] = "<non-serializable>"
        return data

    def __str__(self) -> str:
        tool_status = "bound" if self.tool else "unbound"
        return f"Action({self.name}, id={self.id}, status={self.status}, tool={tool_status})"
