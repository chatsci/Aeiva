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
from typing import Any, Dict, List, Optional

from aeiva.perception.perception import PerceptionNeuron
from aeiva.cognition.cognition import Cognition
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.cognition.memory.memory import MemoryNeuron
from aeiva.cognition.memory.raw_memory import RawMemoryNeuron
from aeiva.cognition.memory.summary_memory import SummaryMemoryNeuron
from aeiva.cognition.emotion.emotion import EmotionNeuron
from aeiva.cognition.goal.goal import GoalNeuron
from aeiva.cognition.world_model.world_model import WorldModelNeuron
from aeiva.event.event_names import EventNames
from aeiva.action.actuator import ActuatorNeuron
from aeiva.neuron import BaseNeuron, Signal
from aeiva.event.event_bus import EventBus
from aeiva.event.event import Event


logger = logging.getLogger(__name__)


class Agent:
    """
    The agent that integrates perception, cognition, memory, and action systems.

    Uses the neuron architecture for all components, with event-driven
    communication between them. Each neuron runs its own processing loop
    via BaseNeuron.run_forever().
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

        # Neurons (initialized in setup)
        self.perception: Optional[PerceptionNeuron] = None
        self.cognition: Optional[Cognition] = None
        self.memory: Optional[MemoryNeuron] = None
        self.raw_memory: Optional[RawMemoryNeuron] = None
        self.raw_memory_summary: Optional[SummaryMemoryNeuron] = None
        self.emotion: Optional[EmotionNeuron] = None
        self.goal: Optional[GoalNeuron] = None
        self.world_model: Optional[WorldModelNeuron] = None
        self.action: Optional[ActuatorNeuron] = None

        # Emotion logging state
        self._last_emotion_log_state: Optional[Dict[str, float]] = None
        self._last_emotion_log_label: Optional[str] = None

    def request_stop(self) -> None:
        """Request the agent to stop its run loop."""
        self._stop_requested = True
        # Stop all neurons
        for neuron in self._get_neurons():
            neuron.stop()

    def _get_neurons(self) -> List[BaseNeuron]:
        """Get list of all active neurons."""
        neurons = [
            self.perception,
            self.cognition,
            self.memory,
            self.raw_memory,
            self.raw_memory_summary,
            self.emotion,
            self.goal,
            self.world_model,
            self.action,
        ]
        return [n for n in neurons if n is not None]

    @staticmethod
    def _config_enabled(config: Optional[Dict], default: bool = True) -> bool:
        """Determine if a subsystem is enabled based on config."""
        if config is None:
            return default
        if isinstance(config, dict) and "enabled" in config:
            return bool(config.get("enabled"))
        return default

    def _create_neurons(self) -> None:
        """Create all neuron instances based on configuration."""
        cfg = self.config_dict

        # Extract configs
        perception_config = cfg.get('perception_config', {})
        cognition_config = cfg
        memory_config = dict(cfg.get('memory_config', {}))
        if "embedder_config" not in memory_config and "embedder_config" in cfg:
            memory_config["embedder_config"] = cfg.get("embedder_config")
        if "storage_config" not in memory_config and "storage_config" in cfg:
            memory_config["storage_config"] = cfg.get("storage_config")
        action_config = cfg.get('action_config', {})
        emotion_config = cfg.get("emotion_config")
        goal_config = cfg.get("goal_config")
        world_model_config = cfg.get("world_model_config")
        raw_memory_config = cfg.get("raw_memory_config")
        raw_memory_summary_config = cfg.get("raw_memory_summary_config")

        # Create neurons
        if self._config_enabled(perception_config, default=True):
            self.perception = PerceptionNeuron(
                name="perception",
                config=perception_config,
                event_bus=self.event_bus
            )

        if self._config_enabled(cfg.get("cognition_config"), default=True):
            brain = LLMBrain(config=cognition_config)
            brain.setup()
            self.cognition = Cognition(
                name="cognition",
                brain=brain,
                event_bus=self.event_bus
            )

        if self._config_enabled(memory_config, default=True):
            self.memory = MemoryNeuron(
                name="memory",
                config=memory_config,
                event_bus=self.event_bus
            )

        if self._config_enabled(raw_memory_config, default=True):
            self.raw_memory = RawMemoryNeuron(
                name="raw_memory",
                config=dict(raw_memory_config or {}),
                event_bus=self.event_bus
            )

        if self._config_enabled(raw_memory_summary_config, default=False):
            summary_cfg = dict(raw_memory_summary_config or {})
            if "raw_memory" not in summary_cfg and raw_memory_config:
                summary_cfg["raw_memory"] = dict(raw_memory_config)
            if "llm_gateway_config" not in summary_cfg:
                summary_cfg["llm_gateway_config"] = cfg.get("llm_gateway_config", {})
            self.raw_memory_summary = SummaryMemoryNeuron(
                name="summary_memory",
                config=summary_cfg,
                event_bus=self.event_bus
            )

        if self._config_enabled(emotion_config, default=True):
            emotion_cfg = dict(emotion_config or {})
            if "llm_gateway_config" not in emotion_cfg:
                emotion_cfg["llm_gateway_config"] = cfg.get("llm_gateway_config", {})
            self.emotion = EmotionNeuron(
                name="emotion",
                config=emotion_cfg,
                event_bus=self.event_bus
            )

        if self._config_enabled(goal_config, default=True):
            goal_cfg = dict(goal_config or {})
            if "llm_gateway_config" not in goal_cfg:
                goal_cfg["llm_gateway_config"] = cfg.get("llm_gateway_config", {})
            self.goal = GoalNeuron(
                name="goal",
                config=goal_cfg,
                event_bus=self.event_bus
            )

        if self._config_enabled(world_model_config, default=True):
            self.world_model = WorldModelNeuron(
                name="world_model",
                config=world_model_config or {},
                event_bus=self.event_bus
            )

        if self._config_enabled(action_config, default=True):
            self.action = ActuatorNeuron(
                name="action",
                config=action_config,
                event_bus=self.event_bus
            )

    async def _setup_neurons(self) -> None:
        """Setup all neurons asynchronously."""
        for neuron in self._get_neurons():
            await neuron.setup()

    def setup(self) -> None:
        """
        Set up all systems (sync version).

        Creates neurons and sets them up. Use setup_async() if already
        in an async context.
        """
        self._create_neurons()

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._setup_neurons())
        else:
            raise RuntimeError("Agent.setup() called inside a running event loop; use await setup_async().")

        self._ensure_emotion_log_file()
        logger.info("Agent setup complete")

    async def setup_async(self) -> None:
        """
        Set up all systems (async version).

        Use this when already in an async context.
        """
        self._create_neurons()
        await self._setup_neurons()
        self._ensure_emotion_log_file()
        logger.info("Agent setup complete")

    async def run(self, raw_memory_session: Optional[Dict[str, Any]] = None) -> None:
        """
        Run the agent event loop.

        This method:
        1. Starts the event bus
        2. Sets up event handlers
        3. Starts perception sensors
        4. Runs all neuron loops via run_forever()
        5. Handles graceful shutdown
        """
        self.event_bus.start()
        self.event_bus.loop = asyncio.get_running_loop()
        self._stop_requested = False

        # Set up event handlers
        self.setup_event_handlers()

        # Start perception sensors
        if self.perception:
            await self.perception.start_sensors()

        # Start raw memory session if provided
        if self.raw_memory and raw_memory_session:
            await self.event_bus.emit(EventNames.RAW_MEMORY_SESSION_START, payload=raw_memory_session)

        # Create tasks for all neuron loops using BaseNeuron.run_forever()
        tasks: List[asyncio.Task] = []
        for neuron in self._get_neurons():
            tasks.append(asyncio.create_task(neuron.run_forever()))

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
            await self._shutdown(tasks, raw_memory_session)

    async def _shutdown(
        self,
        tasks: List[asyncio.Task],
        raw_memory_session: Optional[Dict[str, Any]]
    ) -> None:
        """Gracefully shutdown all neurons and the event bus."""
        # Cancel all neuron tasks
        for task in tasks:
            task.cancel()

        # Wait for tasks to finish with timeout
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # End raw memory session
        if self.raw_memory and raw_memory_session:
            await self.event_bus.emit(EventNames.RAW_MEMORY_SESSION_END, payload=raw_memory_session)
            await self.event_bus.wait_until_all_events_processed()

        # Graceful shutdown for neurons that need special handling
        if self.raw_memory:
            await self.raw_memory.graceful_shutdown()
            await self.event_bus.wait_until_all_events_processed()
        if self.raw_memory_summary:
            await self.raw_memory_summary.graceful_shutdown()
            await self.event_bus.wait_until_all_events_processed()

        # Shutdown remaining neurons
        for neuron in self._get_neurons():
            if neuron not in (self.raw_memory, self.raw_memory_summary):
                try:
                    await neuron.graceful_shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down {neuron.name}: {e}")

        await self.event_bus.wait_until_all_events_processed()
        self.event_bus.stop()
        logger.info("Agent shutdown complete")

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
        """Set up event handlers for cognition output and actions."""
        ui_enabled = bool((self.config_dict.get("agent_config") or {}).get("ui_enabled", True))

        if ui_enabled:
            @self.event_bus.on(EventNames.COGNITION_THOUGHT)
            async def handle_cognition_thought(event: Event):
                """Handle cognition output and route to appropriate interface."""
                payload = event.payload
                streaming = False
                final = True

                if isinstance(payload, Signal):
                    data = payload.data
                    if isinstance(data, dict):
                        response_text = data.get("thought") or data.get("output") or str(data)
                        source_event = data.get("source", payload.source)
                        streaming = bool(data.get("streaming", False))
                        final = bool(data.get("final", True))
                    else:
                        response_text = str(data)
                        source_event = payload.source
                elif isinstance(payload, dict):
                    response_text = payload.get("thought") or payload.get("output") or str(payload)
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

        @self.event_bus.on(EventNames.EMOTION_CHANGED)
        async def handle_emotion_changed(event: Event):
            """Handle emotion updates."""
            payload = event.payload
            if isinstance(payload, Signal):
                payload = payload.data
            show_emotion = bool((self.config_dict.get("agent_config") or {}).get("show_emotion", False))
            if show_emotion or (isinstance(payload, dict) and payload.get("show")):
                await self.handle_terminal_emotion(payload)
            self._record_emotion(payload, event.name)

        @self.event_bus.on(EventNames.GOAL_CHANGED)
        async def handle_goal_changed(event: Event):
            """Handle goal state changes."""
            payload = event.payload
            if isinstance(payload, Signal):
                payload = payload.data
            if isinstance(payload, dict) and payload.get("updates"):
                logger.info("Goal updated: %d changes", len(payload["updates"]))

        @self.event_bus.on(EventNames.AGENT_STOP)
        async def handle_agent_stop(event: Event):
            """Handle agent stop requests."""
            logger.info("Agent stop requested.")
            self.request_stop()

    async def handle_terminal_response_text(self, response_text: str) -> None:
        """Emit response for terminal mode."""
        sys.stdout.write("\r\033[K")
        print("Response: ", end='', flush=True)
        print(f"{response_text}", end='', flush=True)
        print("\nYou: ", end='', flush=True)

    async def handle_terminal_emotion(self, payload: Any) -> None:
        """Emit emotion state to terminal."""
        if not payload:
            return
        label = state = expression = None
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
        """Record emotion to log file."""
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

        # Deduplicate consecutive identical emotions
        if isinstance(state, dict):
            normalized_state = {
                k: round(float(state.get(k, 0.0)), 2)
                for k in ("pleasure", "arousal", "dominance")
            }
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
        """Ensure emotion log file exists."""
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
        """Emit response for Gradio mode."""
        stream = self.config_dict.get("llm_gateway_config", {}).get("llm_stream", False)
        logger.info(f"Handling Gradio response, stream={stream}")

        if response_text:
            await self.event_bus.emit(EventNames.RESPONSE_GRADIO, payload=response_text)
        if stream and final:
            await self.event_bus.emit(EventNames.RESPONSE_GRADIO, payload="<END_OF_RESPONSE>")

    async def handle_realtime_response_text(self, response_text: str, final: bool = True) -> None:
        """Emit response for realtime (voice/video) mode."""
        stream = self.config_dict.get("llm_gateway_config", {}).get("llm_stream", False)
        logger.info(f"Handling realtime response, stream={stream}")

        if response_text:
            await self.event_bus.emit(EventNames.RESPONSE_REALTIME, payload=response_text)
        if stream and final:
            await self.event_bus.emit(EventNames.RESPONSE_REALTIME, payload="<END_OF_RESPONSE>")

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
