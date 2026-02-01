"""
Agent: The central orchestrator integrating perception, cognition, memory, and action.

The Agent coordinates the main systems:
    - Perception: Receives and structures sensory input (via PerceptionNeuron)
    - Cognition: Processes stimuli and generates responses
    - Memory: Stores and retrieves information (via MemoryNeuron)
    - Emotion: Emotional processing (via EmotionNeuron)
    - Goal: Goal management (via GoalNeuron)
    - WorldModel: World state modeling (via WorldModelNeuron)
    - Action: Executes plans and uses tools (via ActuatorNeuron)

Architecture:
    PerceptionNeuron → (Stimuli) → Cognition → Response
                                         → MemoryNeuron → Store/Retrieve
                                         → EmotionNeuron → Emotion State
                                         → GoalNeuron → Goal State
                                         → WorldModelNeuron → World State
                                         → ActuatorNeuron → Execution
"""

import sys
import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

from aeiva.perception.perception import PerceptionNeuron
from aeiva.cognition.cognition import Cognition
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.cognition.memory.memory import MemoryNeuron
from aeiva.cognition.memory.raw_memory import RawMemoryNeuron
from aeiva.cognition.memory.summary_memory import SummaryMemoryNeuron
from aeiva.cognition.emotion.emotion import EmotionNeuron
from aeiva.cognition.goal.goal import GoalNeuron
from aeiva.cognition.world_model.world_model import WorldModelNeuron
from aeiva.action.actuator import ActuatorNeuron
from aeiva.neuron import Signal
from aeiva.event.event_bus import EventBus
from aeiva.event.event import Event


logger = logging.getLogger(__name__)


class Agent:
    """
    The agent that integrates perception, cognition, memory, and action systems.

    Uses the neuron architecture for perception, memory, and action, with event-driven
    communication between components.

    Components:
        - perception: PerceptionNeuron for sensory input
        - cognition: Cognition neuron for reasoning
        - memory: MemoryNeuron for storage and retrieval
        - emotion: EmotionNeuron for emotional processing
        - world_model: WorldModelNeuron for world state modeling
        - action: ActuatorNeuron for plan execution
    """

    def __init__(self, config: Dict):
        """
        Initialize the Agent.

        Args:
            config: Configuration dictionary from YAML/JSON
        """
        self.config_dict = config
        self.config = None
        self.event_bus = EventBus()
        self._stop_requested = False

        # Systems (initialized in setup)
        self.perception: Optional[PerceptionNeuron] = None
        self.cognition: Optional[Cognition] = None
        self.memory: Optional[MemoryNeuron] = None
        self.raw_memory: Optional[RawMemoryNeuron] = None
        self.raw_memory_summary: Optional[SummaryMemoryNeuron] = None
        self.emotion: Optional[Any] = None
        self.goal: Optional[Any] = None
        self.world_model: Optional[WorldModelNeuron] = None
        self.action: Optional[ActuatorNeuron] = None
        self._last_emotion_log_state: Optional[Dict[str, float]] = None
        self._last_emotion_log_label: Optional[str] = None

    def request_stop(self) -> None:
        """Request the agent to stop its run loop."""
        self._stop_requested = True

    @staticmethod
    def _config_enabled(config: Optional[Dict], default: bool = True) -> bool:
        """Determine if a subsystem is enabled based on config."""
        if config is None:
            return default
        if isinstance(config, dict) and "enabled" in config:
            return bool(config.get("enabled"))
        return default

    def _build_emotion_neuron(self, config: Optional[Dict]) -> Optional[Any]:
        """Create an emotion neuron based on configuration."""
        if not self._config_enabled(config, default=True):
            return None

        cfg = dict(config or {})
        if "llm_gateway_config" not in cfg:
            cfg["llm_gateway_config"] = self.config_dict.get("llm_gateway_config", {})
        return EmotionNeuron(name="emotion", config=cfg, event_bus=self.event_bus)

    def _build_goal_neuron(self, config: Optional[Dict]) -> Optional[Any]:
        """Create a goal neuron based on configuration."""
        if not self._config_enabled(config, default=True):
            return None

        cfg = dict(config or {})
        if "llm_gateway_config" not in cfg:
            cfg["llm_gateway_config"] = self.config_dict.get("llm_gateway_config", {})
        return GoalNeuron(name="goal", config=cfg, event_bus=self.event_bus)

    def _build_raw_memory_neuron(self, config: Optional[Dict]) -> Optional[Any]:
        """Create a raw memory neuron based on configuration."""
        if not self._config_enabled(config, default=True):
            return None

        cfg = dict(config or {})
        return RawMemoryNeuron(name="raw_memory", config=cfg, event_bus=self.event_bus)

    def _build_raw_memory_summary_neuron(
        self,
        config: Optional[Dict],
        raw_memory_config: Optional[Dict],
    ) -> Optional[Any]:
        """Create a raw memory summary neuron based on configuration."""
        if not self._config_enabled(config, default=False):
            return None

        cfg = dict(config or {})
        if "raw_memory" not in cfg and raw_memory_config:
            cfg["raw_memory"] = dict(raw_memory_config)
        if "llm_gateway_config" not in cfg:
            cfg["llm_gateway_config"] = self.config_dict.get("llm_gateway_config", {})
        return SummaryMemoryNeuron(name="summary_memory", config=cfg, event_bus=self.event_bus)

    def setup(self) -> None:
        """
        Set up all systems (sync version).

        Uses run_until_complete for async setup. If already in an
        async context, use setup_async() instead.
        """
        perception_config = self.config_dict.get('perception_config', {})
        cognition_enable = self._config_enabled(self.config_dict.get("cognition_config"), default=True)
        cognition_config = self.config_dict
        memory_config = dict(self.config_dict.get('memory_config', {}))
        if "embedder_config" not in memory_config and "embedder_config" in self.config_dict:
            memory_config["embedder_config"] = self.config_dict.get("embedder_config")
        if "storage_config" not in memory_config and "storage_config" in self.config_dict:
            memory_config["storage_config"] = self.config_dict.get("storage_config")
        action_config = self.config_dict.get('action_config', {})
        emotion_config = self.config_dict.get("emotion_config")
        goal_config = self.config_dict.get("goal_config")
        world_model_config = self.config_dict.get("world_model_config")
        raw_memory_config = self.config_dict.get("raw_memory_config")
        raw_memory_summary_config = self.config_dict.get("raw_memory_summary_config")

        # Create perception neuron
        if self._config_enabled(perception_config, default=True):
            self.perception = PerceptionNeuron(
                name="perception",
                config=perception_config,
                event_bus=self.event_bus
            )

        # Create cognition neuron with LLM brain
        if cognition_enable:
            brain = LLMBrain(config=cognition_config)
            brain.setup()
            self.cognition = Cognition(
                name="cognition",
                brain=brain,
                event_bus=self.event_bus
            )

        # Create memory neuron
        if self._config_enabled(memory_config, default=True):
            self.memory = MemoryNeuron(
                name="memory",
                config=memory_config,
                event_bus=self.event_bus
            )

        # Create raw memory neuron (optional)
        self.raw_memory = self._build_raw_memory_neuron(raw_memory_config)
        self.raw_memory_summary = self._build_raw_memory_summary_neuron(
            raw_memory_summary_config,
            raw_memory_config,
        )

        # Create emotion neuron (optional)
        self.emotion = self._build_emotion_neuron(emotion_config)

        # Create goal neuron (optional)
        self.goal = self._build_goal_neuron(goal_config)

        # Create world model neuron (optional)
        if self._config_enabled(world_model_config, default=True):
            self.world_model = WorldModelNeuron(
                name="world_model",
                config=world_model_config or {},
                event_bus=self.event_bus
            )

        # Create action neuron
        if self._config_enabled(action_config, default=True):
            self.action = ActuatorNeuron(
                name="action",
                config=action_config,
                event_bus=self.event_bus
            )

        # Setup all systems
        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(self._setup_neurons())
        except RuntimeError:
            asyncio.get_event_loop().run_until_complete(self._setup_neurons())
        self._ensure_emotion_log_file()

        logger.info("Agent setup complete")

    async def _setup_neurons(self) -> None:
        """Setup async components."""
        if self.perception:
            await self.perception.setup()
        if self.cognition:
            await self.cognition.setup()
        if self.memory:
            await self.memory.setup()
        if self.raw_memory:
            await self.raw_memory.setup()
        if self.raw_memory_summary:
            await self.raw_memory_summary.setup()
        if self.emotion:
            await self.emotion.setup()
        if self.goal:
            await self.goal.setup()
        if self.world_model:
            await self.world_model.setup()
        if self.action:
            await self.action.setup()

    async def setup_async(self) -> None:
        """
        Set up all systems (async version).

        Use this when already in an async context.
        """
        perception_config = self.config_dict.get('perception_config', {})
        cognition_enable = self._config_enabled(self.config_dict.get("cognition_config"), default=True)
        cognition_config = self.config_dict
        memory_config = dict(self.config_dict.get('memory_config', {}))
        if "embedder_config" not in memory_config and "embedder_config" in self.config_dict:
            memory_config["embedder_config"] = self.config_dict.get("embedder_config")
        if "storage_config" not in memory_config and "storage_config" in self.config_dict:
            memory_config["storage_config"] = self.config_dict.get("storage_config")
        action_config = self.config_dict.get('action_config', {})
        emotion_config = self.config_dict.get("emotion_config")
        goal_config = self.config_dict.get("goal_config")
        world_model_config = self.config_dict.get("world_model_config")
        raw_memory_config = self.config_dict.get("raw_memory_config")
        raw_memory_summary_config = self.config_dict.get("raw_memory_summary_config")

        # Create perception neuron
        if self._config_enabled(perception_config, default=True):
            self.perception = PerceptionNeuron(
                name="perception",
                config=perception_config,
                event_bus=self.event_bus
            )

        # Create cognition neuron with LLM brain
        if cognition_enable:
            brain = LLMBrain(config=cognition_config)
            brain.setup()
            self.cognition = Cognition(
                name="cognition",
                brain=brain,
                event_bus=self.event_bus
            )

        # Create memory neuron
        if self._config_enabled(memory_config, default=True):
            self.memory = MemoryNeuron(
                name="memory",
                config=memory_config,
                event_bus=self.event_bus
            )

        # Create raw memory neuron (optional)
        self.raw_memory = self._build_raw_memory_neuron(raw_memory_config)
        self.raw_memory_summary = self._build_raw_memory_summary_neuron(
            raw_memory_summary_config,
            raw_memory_config,
        )

        # Create emotion neuron (optional)
        self.emotion = self._build_emotion_neuron(emotion_config)

        # Create goal neuron (optional)
        self.goal = self._build_goal_neuron(goal_config)

        # Create world model neuron (optional)
        if self._config_enabled(world_model_config, default=True):
            self.world_model = WorldModelNeuron(
                name="world_model",
                config=world_model_config or {},
                event_bus=self.event_bus
            )

        # Create action neuron
        if self._config_enabled(action_config, default=True):
            self.action = ActuatorNeuron(
                name="action",
                config=action_config,
                event_bus=self.event_bus
            )

        # Setup all systems
        await self._setup_neurons()
        self._ensure_emotion_log_file()

        logger.info("Agent setup complete")

    async def run(self, raw_memory_session: Optional[Dict[str, Any]] = None) -> None:
        """
        Run the agent event loop.

        This method:
        1. Starts the event bus
        2. Sets up event handlers
        3. Starts the perception neuron and its sensors
        4. Runs until interrupted
        """
        self.event_bus.start()
        self.event_bus.loop = asyncio.get_running_loop()

        self._stop_requested = False

        # Set up event handlers
        self.setup_event_handlers()

        # Start perception sensors
        if self.perception:
            await self.perception.start_sensors()

        if self.raw_memory and raw_memory_session:
            await self.event_bus.emit("raw_memory.session.start", payload=raw_memory_session)

        # Start neuron processing loops in background
        perception_task = asyncio.create_task(self.run_perception_loop()) if self.perception else None
        cognition_task = asyncio.create_task(self.run_cognition_loop()) if self.cognition else None
        memory_task = asyncio.create_task(self.run_memory_loop()) if self.memory else None
        raw_memory_task = asyncio.create_task(self.run_raw_memory_loop()) if self.raw_memory else None
        raw_memory_summary_task = (
            asyncio.create_task(self.run_raw_memory_summary_loop()) if self.raw_memory_summary else None
        )
        emotion_task = asyncio.create_task(self.run_emotion_loop()) if self.emotion else None
        goal_task = asyncio.create_task(self.run_goal_loop()) if self.goal else None
        world_model_task = asyncio.create_task(self.run_world_model_loop()) if self.world_model else None
        action_task = asyncio.create_task(self.run_action_loop()) if self.action else None

        # Keep running until interrupted
        try:
            while not self._stop_requested:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Agent interrupted by user")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Unexpected error in agent run loop: {e}")
        finally:
            # Graceful shutdown
            if perception_task:
                perception_task.cancel()
            if cognition_task:
                cognition_task.cancel()
            if memory_task:
                memory_task.cancel()
            if emotion_task:
                emotion_task.cancel()
            if goal_task:
                goal_task.cancel()
            if world_model_task:
                world_model_task.cancel()
            if action_task:
                action_task.cancel()
            if self.raw_memory and raw_memory_session:
                await self.event_bus.emit("raw_memory.session.end", payload=raw_memory_session)
                await self.event_bus.wait_until_all_events_processed()
            if self.raw_memory:
                await self.raw_memory.graceful_shutdown()
                await self.event_bus.wait_until_all_events_processed()
            if self.raw_memory_summary:
                await self.raw_memory_summary.graceful_shutdown()
                await self.event_bus.wait_until_all_events_processed()
            if raw_memory_task:
                raw_memory_task.cancel()
            if raw_memory_summary_task:
                raw_memory_summary_task.cancel()
            if self.perception:
                await self.perception.graceful_shutdown()
            if self.memory:
                await self.memory.teardown()
            if self.emotion:
                await self.emotion.graceful_shutdown()
            if self.goal:
                await self.goal.graceful_shutdown()
            if self.world_model:
                await self.world_model.graceful_shutdown()
            if self.action:
                await self.action.graceful_shutdown()
            await self.event_bus.wait_until_all_events_processed()
            self.event_bus.stop()
            logger.info("Agent shutdown complete")

    async def run_perception_loop(self) -> None:
        """Run the perception neuron's processing loop."""
        if not self.perception:
            return
        self.perception.running = True
        try:
            while self.perception.running:
                signal = await self.perception.receive()
                if signal is None:
                    continue

                output = await self.perception.process(signal)
                await self.perception.send(output, parent=signal)
                self.perception.learning.record_activation()

        except asyncio.CancelledError:
            pass
        finally:
            self.perception.running = False

    async def run_cognition_loop(self) -> None:
        """Run the cognition neuron's processing loop."""
        if not self.cognition:
            return
        self.cognition.running = True
        try:
            while self.cognition.running:
                signal = await self.cognition.receive()
                if signal is None:
                    continue

                output = await self.cognition.process(signal)
                await self.cognition.send(output, parent=signal)
                self.cognition.learning.record_activation()

        except asyncio.CancelledError:
            pass
        finally:
            self.cognition.running = False

    async def run_memory_loop(self) -> None:
        """Run the memory neuron's processing loop."""
        if not self.memory:
            return
        self.memory.running = True
        try:
            while self.memory.running:
                signal = await self.memory.receive()
                if signal is None:
                    continue

                output = await self.memory.process(signal)
                await self.memory.send(output, parent=signal)
                self.memory.learning.record_activation()

        except asyncio.CancelledError:
            pass
        finally:
            self.memory.running = False

    async def run_raw_memory_loop(self) -> None:
        """Run the raw memory neuron's processing loop."""
        if not self.raw_memory:
            return
        self.raw_memory.running = True
        try:
            while self.raw_memory.running:
                signal = await self.raw_memory.receive()
                if signal is None:
                    continue

                output = await self.raw_memory.process(signal)
                await self.raw_memory.send(output, parent=signal)
                self.raw_memory.learning.record_activation()
        except asyncio.CancelledError:
            pass
        finally:
            self.raw_memory.running = False

    async def run_raw_memory_summary_loop(self) -> None:
        """Run the raw memory summary neuron's processing loop."""
        if not self.raw_memory_summary:
            return
        self.raw_memory_summary.running = True
        try:
            while self.raw_memory_summary.running:
                signal = await self.raw_memory_summary.receive()
                if signal is None:
                    continue

                output = await self.raw_memory_summary.process(signal)
                await self.raw_memory_summary.send(output, parent=signal)
                self.raw_memory_summary.learning.record_activation()
        except asyncio.CancelledError:
            pass
        finally:
            self.raw_memory_summary.running = False

    async def run_emotion_loop(self) -> None:
        """Run the emotion neuron's processing loop."""
        if not self.emotion:
            return

        self.emotion.running = True
        try:
            while self.emotion.running:
                signal = await self.emotion.receive()
                if signal is None:
                    continue

                output = await self.emotion.process(signal)
                await self.emotion.send(output, parent=signal)
                self.emotion.learning.record_activation()

        except asyncio.CancelledError:
            pass
        finally:
            self.emotion.running = False

    async def run_goal_loop(self) -> None:
        """Run the goal neuron's processing loop."""
        if not self.goal:
            return

        self.goal.running = True
        try:
            while self.goal.running:
                signal = await self.goal.receive()
                if signal is None:
                    continue

                output = await self.goal.process(signal)
                await self.goal.send(output, parent=signal)
                self.goal.learning.record_activation()

        except asyncio.CancelledError:
            pass
        finally:
            self.goal.running = False

    async def run_world_model_loop(self) -> None:
        """Run the world model neuron's processing loop."""
        if not self.world_model:
            return

        self.world_model.running = True
        try:
            while self.world_model.running:
                signal = await self.world_model.receive()
                if signal is None:
                    continue

                output = await self.world_model.process(signal)
                await self.world_model.send(output, parent=signal)
                self.world_model.learning.record_activation()

        except asyncio.CancelledError:
            pass
        finally:
            self.world_model.running = False

    async def run_action_loop(self) -> None:
        """Run the action neuron's processing loop."""
        if not self.action:
            return
        self.action.running = True
        try:
            while self.action.running:
                signal = await self.action.receive()
                if signal is None:
                    continue

                output = await self.action.process(signal)
                await self.action.send(output, parent=signal)
                self.action.learning.record_activation()

        except asyncio.CancelledError:
            pass
        finally:
            self.action.running = False

    async def process_input(self, input_text: str) -> str:
        """
        Process input text and return the agent's response.

        This is a convenience method for direct input processing,
        bypassing the event system. Used by some UI modes.

        Args:
            input_text: User input text

        Returns:
            Agent's response text
        """
        if not self.cognition:
            return ""

        try:
            response = await self.cognition.think(input_text)
            return response
        except Exception as e:
            logger.error(f"Error in process_input: {e}")
            return ""

    def setup_event_handlers(self) -> None:
        """Set up event handlers for perception output and actions."""

        ui_enabled = bool((self.config_dict.get("agent_config") or {}).get("ui_enabled", True))

        if ui_enabled:
            @self.event_bus.on('cognition.thought')
            async def handle_cognition_thought(event: Event):
                """Handle cognition output and route to appropriate interface."""
                payload = event.payload
                streaming = False
                final = True

                if isinstance(payload, Signal):
                    data = payload.data
                    if isinstance(data, dict):
                        if "thought" in data:
                            response_text = data.get("thought")
                        elif "output" in data:
                            response_text = data.get("output")
                        else:
                            response_text = None
                        if response_text is None:
                            response_text = str(data)
                        source_event = data.get("source", payload.source)
                        streaming = bool(data.get("streaming", False))
                        final = bool(data.get("final", True))
                    else:
                        response_text = str(data)
                        source_event = payload.source
                elif isinstance(payload, dict):
                    if "thought" in payload:
                        response_text = payload.get("thought")
                    elif "output" in payload:
                        response_text = payload.get("output")
                    else:
                        response_text = None
                    if response_text is None:
                        response_text = str(payload)
                    source_event = payload.get("source", "unknown")
                    streaming = bool(payload.get("streaming", False))
                    final = bool(payload.get("final", True))
                else:
                    response_text = str(payload)
                    source_event = "unknown"

                if "gradio" in source_event or "gradio" in str(event.name):
                    await self.handle_gradio_response_text(response_text, final=final if streaming else True)
                elif "realtime" in source_event or "realtime" in str(event.name):
                    await self.handle_realtime_response_text(response_text, final=final if streaming else True)
                else:
                    await self.handle_terminal_response_text(response_text)

        if self.action:
            @self.event_bus.on('action.plan')
            async def handle_plan(event: Event):
                """Handle action plans by routing to ActuatorNeuron."""
                plan = event.payload
                result = await self.action.execute_plan(plan)
                logger.info(f"Plan execution result: {result.get('success', False)}")

            @self.event_bus.on('action.result')
            async def handle_action_result(event: Event):
                """Handle action execution results."""
                result = event.payload
                if isinstance(result, Signal):
                    result = result.data
                logger.debug(f"Action result: {result}")

        # Memory event handlers
        @self.event_bus.on('memory.stored')
        async def handle_memory_stored(event: Event):
            """Handle memory storage confirmations."""
            logger.debug(f"Memory stored: {event.payload}")

        @self.event_bus.on('memory.retrieved')
        async def handle_memory_retrieved(event: Event):
            """Handle memory retrieval results."""
            logger.debug(f"Memory retrieved: {event.payload.get('count', 0)} items")

        @self.event_bus.on('emotion.changed')
        async def handle_emotion_changed(event: Event):
            """Handle emotion updates."""
            logger.debug(f"Emotion changed: {event.payload}")
            payload = event.payload
            if isinstance(payload, Signal):
                payload = payload.data
            show_emotion = bool((self.config_dict.get("agent_config") or {}).get("show_emotion", False))
            if show_emotion or (isinstance(payload, dict) and payload.get("show")):
                await self.handle_terminal_emotion(payload)
            self._record_emotion(payload, event.name)

        @self.event_bus.on('goal.changed')
        async def handle_goal_changed(event: Event):
            """Handle goal state changes."""
            payload = event.payload
            if isinstance(payload, Signal):
                payload = payload.data
            if isinstance(payload, dict) and payload.get("updates"):
                logger.info("Goal updated: %d changes", len(payload["updates"]))
            else:
                logger.debug(f"Goal changed: {payload}")

        @self.event_bus.on('world.updated')
        async def handle_world_updated(event: Event):
            """Handle world model updates."""
            logger.debug(f"World updated: {event.payload}")

        # Backward compatibility handlers
        @self.event_bus.on('perception.gradio')
        async def handle_gradio_direct(event: Event):
            """Handle direct Gradio input (backward compatibility)."""
            logger.debug("Received perception.gradio event (handled by PerceptionNeuron)")

        @self.event_bus.on('perception.stimuli')
        async def handle_stimuli_direct(event: Event):
            """Handle direct stimuli input (backward compatibility)."""
            logger.debug("Received perception.stimuli event (handled by PerceptionNeuron)")

        @self.event_bus.on('perception.realtime')
        async def handle_realtime_direct(event: Event):
            """Handle direct realtime input (backward compatibility)."""
            logger.debug("Received perception.realtime event (handled by PerceptionNeuron)")

        @self.event_bus.on('agent.stop')
        async def handle_agent_stop(event: Event):
            """Handle agent stop requests."""
            logger.info("Agent stop requested.")
            self._stop_requested = True

    async def handle_terminal_response_text(self, response_text: str) -> None:
        """
        Emit response for terminal mode.

        Args:
            response_text: Assistant response text
        """
        sys.stdout.write("\r\033[K")
        print("Response: ", end='', flush=True)
        print(f"{response_text}", end='', flush=True)
        print("\nYou: ", end='', flush=True)

    async def handle_terminal_emotion(self, payload: Any) -> None:
        """Emit emotion state to terminal."""
        if not payload:
            return
        label = None
        state = None
        expression = None
        if isinstance(payload, dict):
            label = payload.get("label")
            state = payload.get("state")
            expression = payload.get("expression")
        message = "[Emotion]"
        if label is not None:
            message += f" label={label}"
        if state is not None:
            message += f" state={state}"
        if expression is not None:
            message += f" expression={expression}"
        sys.stdout.write("\r\033[K")
        print(message, flush=True)
        print("You: ", end='', flush=True)

    def _record_emotion(self, payload: Any, source_event: str) -> None:
        agent_cfg = self.config_dict.get("agent_config") or {}
        if not agent_cfg.get("emotion_log_enabled", True):
            return
        if not isinstance(payload, dict):
            return

        path_str = agent_cfg.get("emotion_log_path", "storage/emotion/AgentEmotion.md")
        path = Path(path_str).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            path.write_text("# Agent Emotion Log\n\n", encoding="utf-8")

        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        label = payload.get("label")
        state = payload.get("state")
        expression = payload.get("expression")
        source = payload.get("source", source_event)
        normalized_state = None
        if isinstance(state, dict):
            normalized_state = {
                k: round(float(state.get(k, 0.0)), 2)
                for k in ("pleasure", "arousal", "dominance")
            }
        if normalized_state is not None:
            if (
                self._last_emotion_log_state == normalized_state
                and self._last_emotion_log_label == label
            ):
                return
            self._last_emotion_log_state = normalized_state
            self._last_emotion_log_label = label
        state_text = json.dumps(state, ensure_ascii=False) if isinstance(state, dict) else str(state)
        line = f"- [{timestamp}] label={label} state={state_text} expression={expression} source={source}\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)

    def _ensure_emotion_log_file(self) -> None:
        agent_cfg = self.config_dict.get("agent_config") or {}
        if not agent_cfg.get("emotion_log_enabled", True):
            return
        path_str = agent_cfg.get("emotion_log_path", "storage/emotion/AgentEmotion.md")
        path = Path(path_str).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("# Agent Emotion Log\n\n", encoding="utf-8")

    async def handle_gradio_response_text(self, response_text: str, final: bool = True) -> None:
        """
        Emit response for Gradio mode.

        Args:
            response_text: Assistant response text
        """
        stream = self.config_dict.get("llm_gateway_config", {}).get("llm_stream", False)
        logger.info(f"Handling Gradio response, stream={stream}")

        if response_text:
            await self.event_bus.emit('response.gradio', payload=response_text)
        if stream and final:
            await self.event_bus.emit('response.gradio', payload="<END_OF_RESPONSE>")

    async def handle_realtime_response_text(self, response_text: str, final: bool = True) -> None:
        """
        Emit response for realtime (voice/video) mode.

        Args:
            response_text: Assistant response text
        """
        stream = self.config_dict.get("llm_gateway_config", {}).get("llm_stream", False)
        logger.info(f"Handling realtime response, stream={stream}")

        if response_text:
            await self.event_bus.emit('response.realtime', payload=response_text)
        if stream and final:
            await self.event_bus.emit('response.realtime', payload="<END_OF_RESPONSE>")

    # Legacy properties for backward compatibility
    @property
    def perception_system(self):
        """Backward compatibility: access perception as perception_system."""
        return self.perception

    @property
    def memory_system(self):
        """Backward compatibility: access memory as memory_system."""
        return self.memory

    @property
    def cognition_system(self):
        """Backward compatibility: access cognition as cognition_system."""
        return self.cognition

    @property
    def action_system(self):
        """Backward compatibility: access action as action_system."""
        return self.action
