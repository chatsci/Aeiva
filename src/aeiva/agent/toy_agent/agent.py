# File: aeiva/agent/toy_agent/agent.py

from typing import Any
from aeiva.agent.agent import Agent
from aeiva.agent.toy_agent.cognition_system import ToyCognitionSystem, CognitionError
from aeiva.agent.toy_agent.action_system import ToyActionSystem, ExecutionError
from aeiva.agent.toy_agent.perception_system import ToyPerceptionSystem, PerceptionError
import asyncio

class AgentError(Exception):
    """Exception raised for errors in the Agent."""
    pass

class ToyAgent(Agent):
    """
    A toy implementation of the Agent that integrates CognitionSystem, ActionSystem, and PerceptionSystem.
    """
    
    def __init__(self, config: Any):
        """
        Initialize the Agent with its cognition, perception, and action systems.
        
        Args:
            config (Any): Configuration settings for the Agent.
        """
        super().__init__(config)
        self.cognition_system = ToyCognitionSystem(config.get("cognition", {}))
        self.action_system = ToyActionSystem(config.get("action_system", {}))
        self.perception_system = ToyPerceptionSystem(config.get("perception", {}))

    def initialize_state(self) -> Any:
        """
        Initialize the agent's state.

        Returns:
            Any: The initial state of the agent (e.g., ID, profile, motivation, etc.).
        """
        return {
            "id": self.config.get("id", "agent_1"),
            "profile": self.config.get("profile", {}),
            "motivation": self.config.get("motivation", "explore"),
            "goal": self.config.get("goal", None),
            "task": None,
            "last_observation": None,
            "last_action": None
        }
    
    async def setup(self) -> None:
        """
        Asynchronously set up the Agent's systems.
        """
        try:
            await asyncio.gather(
                self.cognition_system.setup(),
                self.action_system.setup(),
                self.perception_system.setup()
            )
            print("Agent: All systems set up successfully.")
        except Exception as e:
            self.handle_error(e)
            raise AgentError("Failed to set up the Agent.") from e

    async def cycle(self) -> None:
        """
        Execute one cycle of perception, cognition, and action.
        The default behavior is to sense the environment, think, and act.
        """
        try:
            # Simulate receiving a stimulus from the environment
            stimuli = {"type": "sensor_input", "value": "environmental data"}
            print(f"Agent: Sensing stimuli - {stimuli}")

            # Perceive the stimuli
            await self.perception_system.perceive(stimuli)
            observations = self.perception_system.get_observations()
            self.state["last_observation"] = observations
            print(f"Agent: Perceived observations - {observations}")
            
            # Cognitive processing based on the observations
            cognitive_response = await self.cognition_system.think(observations)
            print(f"Agent: Cognitive response - {cognitive_response}")
            
            # Choose and execute an action based on the cognitive response
            action = {"action_type": "respond", "parameters": {"message": cognitive_response}}
            await self.action_system.execute(action)
            self.state["last_action"] = action
        except (CognitionError, PerceptionError, ExecutionError) as e:
            self.handle_error(e)
            raise AgentError("Agent cycle failed.") from e

    async def run(self) -> None:
        """
        Asynchronously run the Agent in a loop, executing cycles of perception, cognition, and action.
        """
        try:
            await self.setup()
            while not self.stop_event.is_set():
                await self.cycle()
                await asyncio.sleep(self.config.get("cycle_interval", 1.0))
        except Exception as e:
            self.handle_error(e)
            raise AgentError("Agent encountered an error during execution.") from e