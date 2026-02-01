"""
ActuatorNeuron: The neuron responsible for executing Plans and Skills.

This neuron follows the receive → process → send pattern:
    1. Receives Plans from cognition (via events)
    2. Converts Plans to Skills and executes them
    3. Emits execution results

Event Flow:
    Cognition → emit('action.plan') → ActuatorNeuron → emit('action.result')

Usage:
    neuron = ActuatorNeuron(
        config=action_config,
        event_bus=bus
    )
    await neuron.setup()
    await neuron.run_forever()
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from aeiva.neuron import BaseNeuron, Signal, NeuronConfig
from aeiva.action.plan import Plan
from aeiva.action.skill import Skill
from aeiva.action.task import Task
from aeiva.action.action import Action
from aeiva.action.status import Status
from aeiva.tool.tool import Tool

if TYPE_CHECKING:
    from aeiva.event.event_bus import EventBus

logger = logging.getLogger(__name__)


def default_input_events() -> List[str]:
    """Default input events for action neuron."""
    return ["action.plan", "action.execute"]


@dataclass
class ActuatorNeuronConfig(NeuronConfig):
    """
    Configuration for ActuatorNeuron.

    Attributes:
        input_events: Event patterns to subscribe to
        output_event: Event name for execution results
        tools: List of tool names to load
        parallel_execution: Whether to execute independent actions in parallel
    """

    input_events: List[str] = field(default_factory=default_input_events)
    output_event: str = "action.result"
    tools: List[str] = field(default_factory=list)
    parallel_execution: bool = False


class ActuatorNeuron(BaseNeuron):
    """
    The action neuron - receives Plans and executes them as Skills.

    This neuron:
    1. Loads and manages tools
    2. Subscribes to action events
    3. Converts Plans to Skills
    4. Executes Skills with proper state management
    5. Emits execution results

    The neuron bridges cognitive outputs (Plans) to executable
    actions (Skills), managing the full execution lifecycle.
    """

    EMISSIONS = ["action.result", "action.progress", "action.error"]
    CONFIG_CLASS = ActuatorNeuronConfig

    def __init__(
        self,
        name: str = "action",
        config: Optional[Dict] = None,
        event_bus: Optional["EventBus"] = None,
        **kwargs
    ):
        """
        Initialize the ActuatorNeuron.

        Args:
            name: Neuron identifier
            config: Configuration dictionary
            event_bus: EventBus for communication
        """
        neuron_config = self.build_config(config or {})
        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)

        # Set subscriptions from config
        self.SUBSCRIPTIONS = self.config.input_events.copy()

        # Tool management
        self.tools: List[Dict] = []
        self.tool_map: Dict[str, Tool] = {}
        self.tool_names: List[str] = config.get("tools", []) if config else []

        # Execution state
        self.current_skill: Optional[Skill] = None
        self.execution_history: List[Dict] = []

        # Identity metadata
        self.identity.data["tools_loaded"] = 0
        self.identity.data["executions_completed"] = 0

    def build_config(self, config_dict: Dict) -> ActuatorNeuronConfig:
        """Build ActuatorNeuronConfig from dictionary."""
        return ActuatorNeuronConfig(
            tools=config_dict.get("tools", []),
            input_events=config_dict.get("input_events", default_input_events()),
            output_event=config_dict.get("output_event", "action.result"),
            parallel_execution=config_dict.get("parallel_execution", False),
        )

    async def setup(self) -> None:
        """Initialize the action neuron and load tools."""
        await super().setup()
        self.load_tools()
        logger.info(f"{self.name} setup complete with {len(self.tools)} tools")

    def load_tools(self) -> None:
        """Load tool schemas from configured tool names."""
        for tool_name in self.tool_names:
            try:
                tool_schema = Tool.load_tool_schema(tool_name)
                self.tools.append(tool_schema)
                self.tool_map[tool_name] = Tool(tool_name)
                logger.debug(f"Loaded tool: {tool_name}")
            except Exception as e:
                logger.warning(f"Failed to load tool '{tool_name}': {e}")

        self.identity.data["tools_loaded"] = len(self.tools)

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tool_map.get(name)

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """
        Process incoming action requests.

        Handles:
            - Plans: Convert to Skill and execute
            - Skills: Execute directly
            - Action requests: Execute single actions

        Args:
            signal: Incoming signal with Plan/Skill/Action data

        Returns:
            Execution result dictionary
        """
        data = signal.data
        source = signal.source

        logger.debug(f"{self.name} processing from {source}: {type(data)}")

        try:
            if isinstance(data, Plan):
                result = await self.execute_plan(data)
            elif isinstance(data, Skill):
                result = await self.execute_skill(data)
            elif isinstance(data, dict):
                # Handle dict-based action requests
                if "plan" in data:
                    plan = self._dict_to_plan(data["plan"])
                    result = await self.execute_plan(plan)
                elif "action" in data:
                    result = await self.execute_single_action(data["action"])
                else:
                    result = {"error": "Unknown action request format"}
            else:
                result = {"error": f"Unsupported data type: {type(data)}"}

            self.identity.data["executions_completed"] += 1
            return result

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {"error": str(e), "success": False}

    async def execute_plan(self, plan: Plan) -> Dict[str, Any]:
        """
        Execute a Plan by converting it to a Skill.

        Args:
            plan: Plan to execute

        Returns:
            Execution result
        """
        logger.info(f"Executing plan: {plan.name} ({plan.id})")

        # Convert plan to skill
        skill = self.plan_to_skill(plan)
        return await self.execute_skill(skill)

    async def execute_skill(self, skill: Skill) -> Dict[str, Any]:
        """
        Execute a Skill.

        Args:
            skill: Skill to execute

        Returns:
            Execution result with status and action results
        """
        logger.info(f"Executing skill: {skill.name} ({skill.id})")
        self.current_skill = skill

        # Bind tools to actions
        for action in skill.actions:
            if action.name in self.tool_map:
                action.bind_tool(self.tool_map[action.name])

        # Execute with callbacks
        async def on_action_complete(action: Action):
            """Emit progress event on action completion."""
            if self.events:
                await self.events.emit(
                    "action.progress",
                    payload={
                        "skill_id": skill.id,
                        "action_id": action.id,
                        "action_name": action.name,
                        "status": str(action.status),
                        "result": action.result,
                    }
                )

        async def on_action_error(action: Action, error: Exception):
            """Emit error event on action failure."""
            logger.error(f"Action '{action.id}' failed: {error}")
            if self.events:
                await self.events.emit(
                    "action.error",
                    payload={
                        "skill_id": skill.id,
                        "action_id": action.id,
                        "action_name": action.name,
                        "error": str(error),
                    }
                )

        try:
            success = await skill.execute(
                on_action_complete=on_action_complete,
                on_action_error=on_action_error
            )

            result = {
                "success": success,
                "skill_id": skill.id,
                "skill_name": skill.name,
                "status": str(skill.status),
                "progress": skill.progress,
                "action_results": {
                    action.id: {
                        "name": action.name,
                        "status": str(action.status),
                        "result": action.result,
                    }
                    for action in skill.actions
                },
            }

            # Record in history
            self.execution_history.append({
                "skill_id": skill.id,
                "success": success,
                "actions": len(skill.actions),
            })

            return result

        except Exception as e:
            return {
                "success": False,
                "skill_id": skill.id,
                "error": str(e),
            }

        finally:
            self.current_skill = None

    async def execute_single_action(self, action_data: Dict) -> Dict[str, Any]:
        """
        Execute a single action from dictionary data.

        Args:
            action_data: Dictionary with action specification

        Returns:
            Action result
        """
        action = Action(
            name=action_data.get("name", "unknown"),
            params=action_data.get("params", {}),
            description=action_data.get("description", ""),
        )

        # Bind tool if available
        if action.name in self.tool_map:
            action.bind_tool(self.tool_map[action.name])

        try:
            result = await action.execute()
            return {
                "success": True,
                "action_id": action.id,
                "result": result,
            }
        except Exception as e:
            return {
                "success": False,
                "action_id": action.id,
                "error": str(e),
            }

    def plan_to_skill(self, plan: Plan) -> Skill:
        """
        Convert a Plan into an executable Skill.

        Args:
            plan: Plan to convert

        Returns:
            Skill with Actions corresponding to Tasks
        """
        actions = []

        for step in plan.steps:
            if isinstance(step, Task):
                action = Action(
                    name=step.name,
                    params=step.params,
                    id=step.id,
                    dependent_ids=step.dependent_ids,
                    description=step.description,
                    metadata=step.metadata,
                )
                actions.append(action)

            elif isinstance(step, Plan):
                # Recursively handle sub-plans
                sub_skill = self.plan_to_skill(step)
                actions.append(sub_skill)

            else:
                raise TypeError(f"Unexpected step type: {type(step)}")

        if not actions:
            raise ValueError(f"Plan '{plan.id}' contains no valid actions")

        return Skill(
            name=plan.name,
            steps=actions,
            id=f"skill_{plan.id}",
            dependent_ids=plan.dependent_ids,
            description=plan.description,
            metadata=plan.metadata,
            parallel=self.config.parallel_execution,
        )

    def _dict_to_plan(self, plan_dict: Dict) -> Plan:
        """Convert dictionary to Plan object."""
        tasks = []
        for step_dict in plan_dict.get("steps", []):
            if step_dict.get("type") == "Plan":
                tasks.append(self._dict_to_plan(step_dict))
            else:
                tasks.append(Task(
                    name=step_dict.get("name", "unknown"),
                    params=step_dict.get("params", {}),
                    id=step_dict.get("id"),
                    dependent_ids=step_dict.get("dependent_ids", []),
                    description=step_dict.get("description", ""),
                    metadata=step_dict.get("metadata", {}),
                ))

        return Plan(
            name=plan_dict.get("name", "unnamed_plan"),
            steps=tasks,
            id=plan_dict.get("id"),
            description=plan_dict.get("description", ""),
            metadata=plan_dict.get("metadata", {}),
        )

    async def send(self, output: Any, parent: Signal = None) -> None:
        """Send execution result to downstream handlers."""
        if output is None:
            return

        if parent:
            signal = parent.child(parent.source, output)
        else:
            signal = Signal(source=self.name, data=output)

        self.working.last_output = output

        if self.events:
            emit_args = self.signal_to_event_args(self.config.output_event, signal)
            await self.events.emit(**emit_args)

    def health_check(self) -> Dict:
        """Return health status including action-specific info."""
        health = super().health_check()
        health.update({
            "tools_loaded": len(self.tools),
            "tools_available": list(self.tool_map.keys()),
            "executions_completed": self.identity.data.get("executions_completed", 0),
            "current_skill": self.current_skill.id if self.current_skill else None,
        })
        return health
