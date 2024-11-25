# File: cognition/simple_mind_manager.py

from cognition.memory.memory import Memory
from cognition.world_model.world_model import WorldModel
from cognition.emotion.emotion import Emotion
from aeiva.cognition.mind_manager.mind_manager import MindManager

from typing import Any, Dict, Optional

class SimpleMindManager(MindManager):
    """
    A simple implementation of the Mind Manager, responsible for updating the Memory, 
    World Model, and Emotion based on input and output data.
    """

    def __init__(self, memory: Memory, world_model: WorldModel, emotion: Emotion, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the SimpleMindManager with the provided Memory, World Model, and Emotion modules.

        Args:
            memory (Memory): The Memory module to be updated.
            world_model (WorldModel): The World Model module to be updated.
            emotion (Emotion): The Emotion module to be updated.
            config (Optional[Dict[str, Any]]): Configuration settings for the Mind Manager.
        """
        super().__init__(config)
        self.memory = memory
        self.world_model = world_model
        self.emotion = emotion

    def update_memory(self, data: Any) -> None:
        """
        Updates the Memory module with new data or feedback.

        Args:
            data (Any): The data to store in memory.
        """
        print(f"Updating memory with data: {data}")
        self.memory.store(data)

    def update_world_model(self, data: Any) -> None:
        """
        Updates the World Model with new data or predictions.

        Args:
            data (Any): The data to update the world model.
        """
        print(f"Updating world model with data: {data}")
        self.world_model.update(data)

    def update_emotion(self, data: Any) -> None:
        """
        Updates the Emotion module based on feedback or changes in the environment.

        Args:
            data (Any): The data to update the emotional state.
        """
        print(f"Updating emotion with data: {data}")
        self.emotion.update(data)

    def trigger_updates(self, input_data: Any, output_data: Any) -> None:
        """
        Triggers updates in the Memory, World Model, and Emotion modules after input and output interactions.

        Args:
            input_data (Any): The input data received by the cognitive system.
            output_data (Any): The output data generated by the cognitive system.
        """
        print("Triggering updates based on input and output...")
        
        # Update memory with input and output data
        self.update_memory({"input": input_data, "output": output_data})

        # Update world model based on output or new observations
        self.update_world_model(output_data)

        # Update emotion based on feedback from the output or environment
        self.update_emotion(output_data)