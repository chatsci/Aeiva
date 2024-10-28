# File: cognition/cognition_system.py

from abc import ABC, abstractmethod
from typing import Any, List


class CognitionSystem(ABC):
    """
    Abstract base class for cognition systems.

    The CognitionSystem is responsible for processing observations to update the cognitive state
    and deciding on actions based on the current cognitive state. It comprises several components:
    brain, world_model, memory, and emotion.

    Attributes:
        config (Any): Configuration settings for the cognition system.
        state (Any): The internal state of the cognition system.
        brain (Any): The cognitive processing unit.
        world_model (Any): The internal model of the environment/world.
        memory (Any): The memory system for storing and retrieving information.
        emotion (Any): The emotion system for managing emotional states.
    """

    def __init__(self, config: Any):
        """
        Initialize the CognitionSystem with the provided configuration.

        Args:
            config (Any): Configuration settings for the cognition system.
        """
        self.config = config
        self.state = self.init_state()
        self.brain = None
        self.world_model = None
        self.memory = None
        self.emotion = None

    @abstractmethod
    def init_state(self) -> Any:
        """
        Initialize the internal state of the cognition system.

        This method should set up the initial state required for the cognition system's operations.

        Returns:
            Any: The initial state of the cognition system.
        """
        pass

    @abstractmethod
    def setup(self) -> None:
        """
        Asynchronously set up the cognition system's components.

        This method should initialize the brain, world_model, memory, and emotion components
        based on the provided configuration.

        Raises:
            ConfigurationError: If the configuration is invalid or incomplete.
        """
        pass

    @abstractmethod
    async def process_observation(self, observation: Any) -> Any:
        """
        Asynchronously process an observation to update the cognitive state.

        Args:
            observation (Any): The current observation to process.

        Returns:
            Any: The updated cognitive state.

        Raises:
            ProcessingError: If processing the observation fails.
        """
        pass

    @abstractmethod
    async def decide_actions(self, cognitive_state: Any) -> Any:
        """
        Asynchronously decide on a list of actions based on the current cognitive state.

        Args:
            cognitive_state (Any): The current cognitive state.

        Returns:
            Any: E.g., a list of actions to perform.

        Raises:
            DecisionError: If action decision fails.
        """
        pass