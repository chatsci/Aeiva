# base_sensor.py

from abc import ABC, abstractmethod
import asyncio

class Sensor(ABC):
    """
    Abstract base class for all sensors.
    """
    def __init__(self, name: str, params: dict, event_bus):
        """
        Initializes the BaseSensor.

        Args:
            name (str): The name of the sensor.
            params (dict): Configuration parameters for the sensor.
            event_bus: The EventBus instance for emitting events.
        """
        self.name = name
        self.params = params
        self.event_bus = event_bus

    @abstractmethod
    async def start(self):
        """
        Starts the sensor.
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Stops the sensor.
        """
        pass