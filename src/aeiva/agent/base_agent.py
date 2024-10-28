# File: agent/agent.py

from abc import ABC, abstractmethod
import asyncio
from typing import Any

from aeiva.perception.perception_system import PerceptionSystem
from aeiva.cognition.cognition_system import CognitionSystem
from aeiva.action.action_system import ActionSystem


class BaseAgent(ABC):
    """
    Abstract base class for autonomous agents with perception, cognition, and action capabilities.
    """

    def __init__(self, config: Any):
        """
        Initialize the agent with configuration.

        Args:
            config (Any): Configuration settings for the agent.
        """
        self.config = config
        self.state = self.initialize_state()  # can be a dict that includes: id, profile, motivation, goal, task, plan, etc.
        self.stop_event = asyncio.Event()

        # Systems will be initialized in the setup method
        self.perception_system: PerceptionSystem = None
        self.cognition_system: CognitionSystem = None
        self.action_system: ActionSystem = None

    @abstractmethod
    def initialize_state(self) -> Any:
        """
        Initialize the agent's state.

        Returns:
            Any: The initial state of the agent.
        """
        pass

    @abstractmethod
    def setup(self) -> None:
        """
        Set up the agent's components (perception, cognition, action, etc.).
        Perform any asynchronous initialization if necessary.
        """
        pass

    @abstractmethod
    async def cycle(self) -> None:
        """
        Execute one cycle of perception, cognition, and action.
        This method should be overridden to define the agent's behavior per cycle.
        """
        pass

    async def run(self) -> None:
        """
        Run the agent, continuously executing cycles until stopped.
        """
        await self.setup()
        cycle_interval = self.config.get('cycle_interval', 1.0)
        while not self.stop_event.is_set():
            try:
                await self.cycle()
            except Exception as e:
                self.handle_error(e)
            await asyncio.sleep(cycle_interval)

    def stop(self) -> None:
        """
        Signal the agent to stop running.
        """
        self.stop_event.set()

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during cycle execution.

        Args:
            error (Exception): The exception that was raised.
        """
        # Implement your error handling logic here (e.g., logging)
        print(f"Error during agent cycle: {error}")