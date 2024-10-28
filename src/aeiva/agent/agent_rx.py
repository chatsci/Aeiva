# File: agent/agent.py

import os
import asyncio
from typing import Any

from aeiva.perception.perception_system import PerceptionSystem
from aeiva.cognition.cognition_system import CognitionSystem
from aeiva.action.action_system import ActionSystem
from aeiva.cognition.input_interpreter.simple_input_interpreter import SimpleInputInterpreter
from aeiva.cognition.output_orchestrator.simple_output_orchestrator import SimpleOutputOrchestrator
from aeiva.cognition.memory.simple_memory import SimpleMemory
from aeiva.cognition.emotion.simple_emotion import SimpleEmotion
from aeiva.cognition.world_model.simple_world_model import SimpleWorldModel
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.cognition.brain.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.action.plan import Plan
from aeiva.cognition.thought import Thought


class Agent:
    """
    Represents the agent that integrates perception, cognition, and action systems.
    """
    def __init__(self, perception_config: Any, cognition_components: Any, action_config: Any):
        self.perception_system = PerceptionSystem(perception_config)
        self.cognition_system = CognitionSystem(**cognition_components)
        self.action_system = ActionSystem(action_config)
        self.loop = asyncio.get_event_loop()

    def setup(self) -> None:
        """
        Set up all systems.
        """
        self.perception_system.setup()
        self.cognition_system.setup()
        self.action_system.setup()

    def run(self) -> None:
        """
        Run the agent by connecting perception, cognition, and action systems.
        """
        observation_stream = self.perception_system.perceive()

        def on_next(stimuli):
            asyncio.run(self.handle_stimuli(stimuli))

        def on_error(e):
            print(f"Error: {e}")

        def on_completed():
            print("Perception stream completed.")

        # Subscribe to the observation stream
        observation_stream.subscribe(
            on_next=on_next,
            on_error=on_error,
            on_completed=on_completed
        )

    async def handle_stimuli(self, stimuli):
        # Process stimuli through cognition system
        output = await self.cognition_system.think(stimuli)

        # Determine if output is a Plan or Thought
        if isinstance(output, Plan):
            # Pass the plan to the action system
            await self.action_system.execute(output)
        elif isinstance(output, Thought):
            # Handle direct response (e.g., print to user)
            print(f"Agent Response: {output.content}")
        else:
            print("Unknown output from cognition system.")



def main():
    # Load environment variables and set up LLMBrain
    API_KEY = os.getenv('OPENAI_API_KEY')
    config = LLMGatewayConfig(
        llm_api_key=API_KEY,
        llm_model_name="gpt-4-turbo",
        llm_temperature=0.7,
        llm_max_output_tokens=1000,
        llm_logging_level="info",
        llm_stream=True
    )
    llm_brain = LLMBrain(config)

    # Define configurations
    perception_config = {
        "sensors": [
            {
                "sensor_name": "percept_terminal_input",
                "sensor_params": {"prompt_message": "You: "}
            }
        ]
    }

    cognition_components = {
        "input_interpreter": SimpleInputInterpreter(),
        "brain": llm_brain,  # Assuming llm_brain is an instance of your Brain class
        "output_orchestrator": SimpleOutputOrchestrator(),
        "memory": SimpleMemory(),
        "emotion": SimpleEmotion(),
        "world_model": SimpleWorldModel(),
        "config": None
    }

    action_config = {
        # Include any configurations needed for your ActionSystem
    }

    # Create agent instance
    agent = Agent(perception_config, cognition_components, action_config)
    agent.setup()
    agent.run()

if __name__ == "__main__":
    main()