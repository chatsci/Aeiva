"""
PerceptionNeuron: The neuron responsible for receiving and processing sensory input.

This neuron replaces the old PerceptionSystem, providing a cleaner architecture
based on the receive → process → send pattern. It manages sensors and converts
raw input into structured Stimuli for downstream processing.

Usage:
    neuron = PerceptionNeuron(
        name="perception",
        config=perception_config,
        event_bus=bus
    )
    await neuron.setup()
    await neuron.start_sensors()
    await neuron.run_forever()

Event Flow:
    Sensors → emit('perception.stimuli') → PerceptionNeuron → emit('perception.output')
    Gradio  → emit('perception.gradio')  → PerceptionNeuron → emit('perception.output')

The 'perception.output' event contains:
    - signal.data: Stimuli object
    - signal.source: "perception"
    - Metadata for tracing (trace_id, parent_id, etc.)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from aeiva.neuron import BaseNeuron, Signal, NeuronConfig
from aeiva.perception.stimuli import Stimuli
from aeiva.perception.sensation import Signal as PerceptionSignal
from aeiva.perception.sensor.sensor import Sensor
from aeiva.perception.sensor.terminal_input_sensor import TerminalInputSensor

if TYPE_CHECKING:
    from aeiva.event.event_bus import EventBus

logger = logging.getLogger(__name__)


def default_input_events() -> List[str]:
    """Default input events for perception."""
    return [
        "perception.stimuli",   # Terminal input
        "perception.gradio",    # Gradio input
        "perception.api",       # API input
        "perception.realtime",  # Realtime voice/video input
    ]


@dataclass
class PerceptionNeuronConfig(NeuronConfig):
    """
    Configuration for PerceptionNeuron.

    Attributes:
        input_events: Event patterns to subscribe to for input
        output_event: Event name to emit processed stimuli
        default_modality: Default modality for incoming signals
        sensors: List of sensor configurations
    """
    input_events: List[str] = field(default_factory=default_input_events)
    output_event: str = "perception.output"
    default_modality: str = "text"
    sensors: List[Dict] = field(default_factory=list)


class PerceptionNeuron(BaseNeuron):
    """
    The perception neuron - receives sensory input and emits structured Stimuli.

    This neuron:
    1. Manages sensors (terminal, GUI, API inputs)
    2. Subscribes to sensor events
    3. Converts raw input to Stimuli
    4. Emits standardized 'perception.output' events

    The neuron fully replaces the old PerceptionSystem while maintaining
    backward compatibility with existing sensors and event names.
    """

    EMISSIONS = ["perception.output"]
    CONFIG_CLASS = PerceptionNeuronConfig

    def __init__(
        self,
        name: str = "perception",
        config: Dict = None,
        event_bus: "EventBus" = None,
        **kwargs
    ):
        """
        Initialize the PerceptionNeuron.

        Args:
            name: Neuron identifier
            config: Configuration dictionary (from agent_config.yaml perception_config)
            event_bus: EventBus for communication
        """
        # Build neuron config from dict config
        neuron_config = self.build_config(config or {})
        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)

        # Set subscriptions from config
        self.SUBSCRIPTIONS = self.config.input_events.copy()

        # Sensor management
        self.sensors: List[Sensor] = []
        self.sensor_configs = config.get("sensors", []) if config else []

        # Track input sources and metadata
        self.identity.data["input_sources"] = []
        self.identity.data["sensors_active"] = False

    def build_config(self, config_dict: Dict) -> PerceptionNeuronConfig:
        """
        Build PerceptionNeuronConfig from a dictionary.

        Args:
            config_dict: Configuration dictionary from YAML/JSON

        Returns:
            PerceptionNeuronConfig instance
        """
        return PerceptionNeuronConfig(
            sensors=config_dict.get("sensors", []),
            input_events=config_dict.get("input_events", default_input_events()),
            output_event=config_dict.get("output_event", "perception.output"),
            default_modality=config_dict.get("default_modality", "text"),
        )

    async def setup(self) -> None:
        """
        Initialize the perception neuron and create sensors.

        This method:
        1. Calls parent setup (queue, subscriptions)
        2. Creates configured sensors
        """
        await super().setup()
        self.setup_sensors()
        logger.info(f"{self.name} setup complete with {len(self.sensors)} sensors")

    def setup_sensors(self) -> None:
        """
        Create and configure sensors based on config.

        Sensors are created but not started - call start_sensors() to begin sensing.
        """
        for sensor_config in self.sensor_configs:
            sensor_name = sensor_config.get("sensor_name")
            sensor_params = sensor_config.get("sensor_params", {})

            sensor = self.create_sensor(sensor_name, sensor_params)
            if sensor:
                self.sensors.append(sensor)
                logger.info(f"{self.name} created sensor: {sensor_name}")
            else:
                logger.warning(f"{self.name} unknown sensor type: {sensor_name}")

    def create_sensor(self, sensor_name: str, params: Dict) -> Optional[Sensor]:
        """
        Factory method to create sensors by name.

        Override this method to add custom sensor types.

        Args:
            sensor_name: Name/type of the sensor
            params: Sensor configuration parameters

        Returns:
            Sensor instance or None if unknown type
        """
        if sensor_name == "percept_terminal_input":
            return TerminalInputSensor(sensor_name, params, self.events)
        # Add more sensor types here as needed
        return None

    async def start_sensors(self) -> None:
        """
        Start all configured sensors.

        Sensors begin emitting events to the EventBus, which this neuron
        receives and processes.
        """
        logger.info(f"{self.name} starting {len(self.sensors)} sensors")
        for sensor in self.sensors:
            await sensor.start()
        self.identity.data["sensors_active"] = True

    async def stop_sensors(self) -> None:
        """
        Stop all sensors gracefully.
        """
        logger.info(f"{self.name} stopping sensors")
        for sensor in self.sensors:
            await sensor.stop()
        self.identity.data["sensors_active"] = False

    async def process(self, signal: Signal) -> Optional[Stimuli]:
        """
        Process incoming sensory signal into structured Stimuli.

        This method:
        1. Extracts raw data from the signal
        2. Determines the input source and modality
        3. Creates a structured Stimuli object

        Args:
            signal: Incoming signal with sensory data

        Returns:
            Structured Stimuli object
        """
        # Track input source
        source = signal.source
        if source not in self.identity.data["input_sources"]:
            self.identity.data["input_sources"].append(source)

        # Extract raw data
        raw_data = signal.data

        # Handle different input formats
        if isinstance(raw_data, Stimuli):
            # Already structured, pass through
            return raw_data

        meta = None
        if isinstance(raw_data, dict):
            # Structured input with metadata
            data = raw_data.get("data", raw_data)
            modality = raw_data.get("modality", self.config.default_modality)
            meta = raw_data.get("meta") or raw_data.get("metadata")
        else:
            # Raw input (string, bytes, etc.)
            data = raw_data
            modality = self.detect_modality(raw_data)

        # Create perception signal
        perception_signal = PerceptionSignal(
            data=data,
            modularity=modality,
            type="input",
            metadata=meta if isinstance(meta, dict) else {},
        )

        # Create stimuli
        stimuli = Stimuli(
            signals=[perception_signal],
            metadata=meta if isinstance(meta, dict) else {},
        )

        logger.debug(f"{self.name} processed input: source={source}, modality={modality}")
        return stimuli

    def detect_modality(self, data: Any) -> str:
        """
        Detect the modality of incoming data.

        Args:
            data: Raw input data

        Returns:
            Detected modality string
        """
        if isinstance(data, str):
            return "text"
        elif isinstance(data, bytes):
            return "binary"
        elif hasattr(data, 'shape'):
            # Numpy array - likely image or audio
            return "array"
        else:
            return self.config.default_modality

    async def send(self, output: Any, parent: Signal = None) -> None:
        """
        Send processed Stimuli to downstream neurons/handlers.

        Emits to the configured output event (default: 'perception.output').

        The output signal preserves the original input source for routing
        decisions downstream (e.g., gradio vs terminal responses).
        """
        if output is None:
            return

        # Determine the source - use original input source for routing
        # This allows downstream handlers to know if input came from gradio/terminal/etc.
        if parent:
            original_source = parent.source
            signal = parent.child(original_source, output)
        else:
            signal = Signal(source=self.name, data=output)

        self.working.last_output = output

        if self.events:
            emit_args = self.signal_to_event_args(self.config.output_event, signal)
            await self.events.emit(**emit_args)

    async def teardown(self) -> None:
        """
        Clean up resources including stopping sensors.
        """
        await self.stop_sensors()
        await super().teardown()

    def health_check(self) -> dict:
        """
        Return health status including perception-specific info.
        """
        health = super().health_check()
        health["input_sources"] = self.identity.data.get("input_sources", [])
        health["sensors_count"] = len(self.sensors)
        health["sensors_active"] = self.identity.data.get("sensors_active", False)
        return health
