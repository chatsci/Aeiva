# agent.py

import os
import sys
import asyncio
import threading
import logging
import warnings
from datetime import datetime, timezone
from typing import Any
import json

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
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.action.plan import Plan
from aeiva.cognition.thought import Thought
from aeiva.perception.sensation import Signal
from aeiva.perception.stimuli import Stimuli
# Import Event and EventBus from their modules
from aeiva.event.event_bus import EventBus, EventCancelled
from aeiva.event.event import Event



# # Suppress DeprecationWarning for datetime
# warnings.filterwarnings("ignore", category=DeprecationWarning)

# # Configure logging to console for debugging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s:%(name)s:%(message)s'
# )
# logger = logging.getLogger('agent')


# Agent class
class Agent:
    """
    Represents the agent that integrates perception, cognition, and action systems.
    """
    def __init__(self, perception_config: Any, cognition_components: Any, action_config: Any):
        self.event_bus = EventBus()
        self.perception_system = PerceptionSystem(perception_config, self.event_bus)
        self.cognition_system = CognitionSystem(**cognition_components)
        self.action_system = ActionSystem(action_config)

    def setup(self) -> None:
        """
        Set up all systems.
        """
        self.perception_system.setup()
        self.cognition_system.setup()
        self.action_system.setup()

    async def run(self) -> None:
        """
        Run the agent by connecting perception, cognition, and action systems using the event bus.
        """
        # Start the event bus within the running event loop
        self.event_bus.start()
        # Set up event handlers
        self.setup_event_handlers()
        # Start the perception system
        await self.perception_system.start()

        # Keep the event loop running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            # Handle graceful shutdown
            self.perception_system.stop()
            await self.event_bus.wait_until_all_events_processed()
            self.event_bus.stop()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            # logger.error(f"Unexpected error in agent run loop: {e}")
            print(f"Unexpected error in agent run loop: {e}", flush=True)
            await self.perception_system.stop()
            await self.event_bus.wait_until_all_events_processed()
            self.event_bus.stop()

    def setup_event_handlers(self) -> None:
        """
        Set up event handlers for perception, cognition, and action events.
        """

        @self.event_bus.on('perception.stimuli')
        async def handle_stimuli(event: Event):
            # print("handle_stimuli called", flush=True)
            stimuli = event.payload
            #print(f"Received stimuli: {stimuli}", flush=True)
            # Process stimuli through cognition system
            #stimuli = [{"role": "user", "content": stimuli}]
            stimuli = Stimuli(signals=[Signal(data=stimuli, modularity='text')])
            output = await self.cognition_system.think(stimuli, stream=False, tools=self.action_system.tools)

            # Print in non-stream mode. Small bug in stream mode.
            sys.stdout.write("\r\033[K")  # Return to start of the line and clear it\
            print(f"Response: {output.content}\nYou: ", end='', flush=True)
            
            # # Determine if output is a Plan or Thought
            # if isinstance(output, Plan):  # TODO: change later
            #     print("Output is a Plan", flush=True)
            #     await self.event_bus.emit('action.plan', payload=output)
            # elif isinstance(output, Thought):
            #     print("Output is a Thought", flush=True)
            #     print(f"Agent Response: {output.content}", flush=True)
            # else:
            #     print("Unknown output from cognition system.", flush=True)

        @self.event_bus.on('action.plan')
        async def handle_plan(event: Event):
            print("handle_plan called", flush=True)
            plan = event.payload
            await self.action_system.execute(plan)







# Main function
def main():
    # Define configurations
    perception_config = {
        "sensors": [
            {
                "sensor_name": "percept_terminal_input",
                "sensor_params": {"prompt_message": "You: "}
            }
        ]
    }

    # Load environment variables and set up LLMBrain
    API_KEY = os.getenv('OPENAI_API_KEY')
    config = LLMGatewayConfig(
        llm_api_key=API_KEY,
        llm_model_name="gpt-4-turbo",
        llm_temperature=0.7,
        llm_max_output_tokens=1000,
        # llm_logging_level="info",
        llm_stream=True
    )
    llm_brain = LLMBrain(config)
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
        "tools": ["test_operation"]
    }

    # Create agent instance
    agent = Agent(perception_config, cognition_components, action_config)
    agent.setup()

    # Run the agent
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()