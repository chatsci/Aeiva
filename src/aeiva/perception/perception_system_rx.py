import reactivex as rx
from reactivex import operators as ops
from typing import List, Callable, Any
import logging
import asyncio
from aeiva.perception.sensor_rx import Sensor
from aeiva.perception.stimuli import Stimuli
from aeiva.perception.sensation import Signal


class PerceptionSystem:
    """
    Manages multiple sensors, processes their data streams, and produces observations.
    """

    def __init__(self, config: Any):
        """
        Initializes the PerceptionSystem with a list of sensors.

        Args:
            sensors: A list of Sensor instances.
        """
        self.config = config
        self.sensors = None
        self.observation_stream = None

    def setup(self) -> None:
        """Sets up the perception system."""
        # Additional setup tasks can be added here
        self.sensors = []
        for sensor in self.config["sensors"]:
            self.sensors.append(Sensor(sensor["sensor_name"], sensor["sensor_params"]))
        logging.info("PerceptionSystem setup complete.")

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

    def perceive(self) -> rx.Observable:
        """
        Subscribes to all sensor streams and processes the data.

        Returns:
            An Observable emitting processed observations.
        """
        # Create a list of observables from all sensors
        sensor_streams = [sensor.percept() for sensor in self.sensors]

        # Merge all sensor streams into one observable
        merged_stream = rx.merge(*sensor_streams)
        # # Or, Combines items from each observable into tuples, emitting them only when each observable has emitted an item.
        # combined_stream = rx.zip(*sensor_streams)

        # Process the merged data stream
        self.observation_stream = merged_stream.pipe(
            ops.map(self.signal_to_stimuli),
            ops.do_action(on_error=self.handle_error)
        )
        return self.observation_stream

    def handle_error(self, error: Exception) -> None:
        """Handles errors in the data stream."""
        logging.error(f"PerceptionSystem error: {error}")