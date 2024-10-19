# File: aeiva/agent/toy_agent/cognition_system.py

from typing import Any
from aeiva.cognition.cognition_system import CognitionSystem  # Assuming abstract CognitionSystem is defined here
from aeiva.agent.toy_agent.brain import ToyBrain
from aeiva.agent.toy_agent.memory import ToyMemory
from aeiva.agent.toy_agent.world_model import ToyWorldModel
from aeiva.agent.toy_agent.emotion import ToyEmotion
import asyncio

class CognitionError(Exception):
    """Exception raised for errors in the Cognition system."""
    pass

class ToyCognitionSystem(CognitionSystem):
    """
    A toy implementation of the Cognition System that integrates Brain, Memory, WorldModel, and Emotion.
    """
    
    def __init__(self, config: Any):
        """
        Initialize the Cognition System with its components.
        
        Args:
            config (Any): Configuration settings for the Cognition System.
        """
        super().__init__(config)
        self.state = self.init_state()
        self.brain = ToyBrain(config.get("brain", {}))
        self.memory = ToyMemory(config.get("memory", {}))
        self.world_model = ToyWorldModel(config.get("world_model", {}))
        self.emotion = ToyEmotion(config.get("emotion", {}))
    
    def init_state(self) -> Any:
        """
        Initialize the Cognition System's internal state.

        Returns:
            Any: The initial state of the Cognition System.
        """
        return {
            "last_observation": None,
            "last_response": None,
            "cognitive_state": {}
        }
    
    async def setup(self) -> None:
        """
        Asynchronously set up the Cognition System's components.
        """
        try:
            await asyncio.gather(
                self.brain.setup(),
                self.memory.setup(),
                self.world_model.setup(),
                self.emotion.setup()
            )
            print("CognitionSystem: All components set up successfully.")
        except Exception as e:
            self.handle_error(e)
            raise CognitionError("Failed to set up Cognition System.") from e

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
        try:
            # Update the WorldModel with the new observation
            await self.world_model.update(observation)
            
            # Use Brain to process the observation and update the cognitive state
            response = await self.brain.think(observation)
            self.state["last_observation"] = observation
            self.state["last_response"] = response

            # Optionally store the observation in Memory
            await self.memory.store({"key": "last_observation", "value": observation})
            
            # Return the updated cognitive state
            return self.state

        except Exception as e:
            self.handle_error(e)
            raise CognitionError("Failed to process the observation.") from e

    async def decide_actions(self, cognitive_state: Any) -> Any:
        """
        Asynchronously decide on a list of actions based on the current cognitive state.

        Args:
            cognitive_state (Any): The current cognitive state.

        Returns:
            Any: A list of actions to perform or a response.

        Raises:
            CognitionError: If action decision fails.
        """
        try:
            # Use Brain to decide on an action based on the cognitive state
            response = await self.brain.think(cognitive_state["last_observation"])
            self.state["last_response"] = response
            
            # Store the response in Memory
            await self.memory.store({"key": "last_response", "value": response})
            
            # Update WorldModel with the new action data (if necessary)
            await self.world_model.update({
                "entity": {
                    "id": "response_entity",
                    "type": "response",
                    "attributes": {"content": response}
                }
            })
            
            # Adjust Emotion based on the response
            emotion = "happy" if "happy" in response.lower() else "neutral"
            await self.emotion.set_emotion(emotion)
            
            return response
        except Exception as e:
            self.handle_error(e)
            raise CognitionError("Failed during the cognitive action decision.") from e

    def handle_error(self, error: Exception) -> None:
        """
        Handle errors that occur during cognition operations.

        Args:
            error (Exception): The exception that was raised.
        """
        print(f"Error in ToyCognitionSystem: {error}")
