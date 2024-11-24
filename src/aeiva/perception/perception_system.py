# perception_system.py

import asyncio
import logging
from typing import Any, List, Dict
from aeiva.perception.sensor import Sensor
from aeiva.perception.stimuli import Stimuli
from aeiva.perception.sensation import Signal
from aeiva.perception.terminal_input_sensor import TerminalInputSensor

class PerceptionSystem:
    """
    Manages multiple sensors and emits stimuli via the EventBus.
    """
    def __init__(self, config: Dict, event_bus):
        """
        Initializes the PerceptionSystem with a list of sensors.

        Args:
            config (Any): Configuration dictionary for the sensors.
            event_bus: The EventBus instance for emitting events.
        """
        self.config = config
        self.event_bus = event_bus
        self.sensors: List[Sensor] = []
        self.logger = logging.getLogger('PerceptionSystem')

    def setup(self) -> None:
        """
        Sets up the perception system by initializing all configured sensors.
        """
        for sensor_config in self.config.get("sensors", []):
            sensor_name = sensor_config.get("sensor_name")
            sensor_params = sensor_config.get("sensor_params", {})
            # TODO: revise later
            if sensor_name == 'percept_terminal_input':
                sensor = TerminalInputSensor(sensor_name, sensor_params, self.event_bus)
                self.sensors.append(sensor)
            else:
                self.logger.warning(f"Unknown sensor type: {sensor_name}")
        self.logger.info("PerceptionSystem setup complete.")

    async def start(self) -> None:  # TODO: maybe rename in the future
        """
        Starts all sensors asynchronously.
        """
        self.logger.info("Starting all sensors.")
        for sensor in self.sensors:
            await sensor.start()

    async def stop(self) -> None:
        """
        Stops all sensors asynchronously.
        """
        self.logger.info("Stopping all sensors.")
        for sensor in self.sensors:
            await sensor.stop()

    def signal_to_stimuli(self, data: Any) -> Any:
        """
        Processes raw data from sensors into structured stimuli.

        Args:
            data: The raw data emitted by sensors.

        Returns:
            Processed data (stimuli).
        """
        # Implement your data processing logic here
        signal = Signal(
            data=data,
            modularity="text",  # Or appropriate modality
            type="input",       # Or appropriate type
            # TODO: After revised Sensor class, Include other metadata as needed
        )
        stimuli = Stimuli(signals=[signal])  # TODO: add more fields
        return stimuli