from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class MindManager(ABC):
    """
    Abstract base class for the Mind Manager, responsible for triggering updates in Memory,
    World Model, and Emotion based on input and output interactions with the cognitive system.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the Mind Manager with optional configuration.
        """
        self.config = config or {}

    @abstractmethod
    def update_memory(self, data: Any) -> None:
        """
        Updates the Memory module with new data or feedback.
        """
        pass

    @abstractmethod
    def update_world_model(self, data: Any) -> None:
        """
        Updates the World Model with new data or predictions.
        """
        pass

    @abstractmethod
    def update_emotion(self, data: Any) -> None:
        """
        Updates the Emotion module based on feedback or changes in the environment.
        """
        pass

    @abstractmethod
    def trigger_updates(self, input_data: Any, output_data: Any) -> None:
        """
        Triggers updates in the Memory, World Model, and Emotion modules after input and output interactions.
        """
        pass