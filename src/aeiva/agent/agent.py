# agent.py

import os
import sys
import asyncio
import threading
import logging
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json

import os
import asyncio
from typing import Any

from aeiva.perception.perception_system import PerceptionSystem
from aeiva.cognition.cognition_system import CognitionSystem
from aeiva.action.action_system import ActionSystem
from aeiva.action.plan import Plan
from aeiva.cognition.thought import Thought
from aeiva.perception.sensation import Signal
from aeiva.perception.stimuli import Stimuli
# Import Event and EventBus from their modules
from aeiva.event.event_bus import EventBus, EventCancelled
from aeiva.event.event import Event

from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


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
    def __init__(self, config: Dict):
        self.config_dict = config
        self.config = None
        self.event_bus = EventBus()
        self.perception_system = None
        self.cognition_system = None
        self.action_system = None

    def setup(self) -> None:
        """
        Set up all systems.
        """
        perception_config = self.config_dict.get('perception_config', {})
        cognition_config = self.config_dict  # NOTE: we didn't define a cognition config class yet.
        action_config = self.config_dict.get('action_config', {})
        
        self.perception_system = PerceptionSystem(perception_config, self.event_bus)
        self.cognition_system = CognitionSystem(cognition_config)
        self.action_system = ActionSystem(action_config)

        self.perception_system.setup()
        self.cognition_system.setup()
        self.action_system.setup()

    async def run(self) -> None:
        """
        Run the agent by connecting perception, cognition, and action systems using the event bus.
        """
        # Start the event bus within the running event loop
        self.event_bus.start()
        # Assign the current running loop to the EventBus
        self.event_bus.loop = asyncio.get_running_loop()
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

    async def process_input(self, input_text: str) -> str:
        """
        Process input text and return the agent's response.
        """
        stream = self.config_dict.get("llm_gateway_config").get("llm_stream")
        use_async = self.config_dict.get("llm_gateway_config").get("llm_use_async")
        stimuli = Stimuli(signals=[Signal(data=input_text, modularity='text')])
        output = ""
        try:
            response_gen = self.cognition_system.think(stimuli, tools=self.action_system.tools, stream=stream, use_async=use_async)
            async for chunk in response_gen:
                if isinstance(chunk, str):
                    # For streaming chunks
                    output += chunk
                elif isinstance(chunk, Thought) or isinstance(chunk, Plan):
                    # For non-streaming responses
                    output += chunk.content
        except Exception as e:
            logger.error(f"Error in response: {e}")
        return output

    def setup_event_handlers(self) -> None:
        """
        Set up event handlers for perception, cognition, and action events.
        """

        @self.event_bus.on('perception.stimuli')
        async def handle_stimuli(event: Event):
            # print("handle_stimuli called", flush=True)
            user_input = event.payload
            stimuli = Stimuli(signals=[Signal(data=user_input, modularity='text')])
            #print(f"Received stimuli: {stimuli}", flush=True)
            # Process stimuli through cognition system
            #stimuli = [{"role": "user", "content": stimuli}]

            stream = self.config_dict.get("llm_gateway_config").get("llm_stream")
            use_async = self.config_dict.get("llm_gateway_config").get("llm_use_async")
            sys.stdout.write("\r\033[K")  # Return to start of the line and clear it\
            print("Response: ", end='', flush=True)
            
            try:
                response_gen = self.cognition_system.think(stimuli, tools=self.action_system.tools, stream=stream, use_async=use_async)
                async for chunk in response_gen:
                    if isinstance(chunk, str):
                        # For streaming chunks
                        print(f"{chunk}", end='', flush=True)
                    elif isinstance(chunk, Thought) or isinstance(chunk, Plan):
                        # For non-streaming responses
                        print(f"{chunk.content}", end='', flush=True)
            except Exception as e:
                logger.error(f"Error in response: {e}")
            
            print("\nYou: ", end='', flush=True)
            
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

        @self.event_bus.on('perception.gradio')
        async def handle_gradio_input(event: Event):
            """
            Handle input from Gradio and emit response.gradio events.
            """
            user_input = event.payload
            stimuli = Stimuli(signals=[Signal(data=user_input, modularity='text')])
            
            stream = self.config_dict.get("llm_gateway_config").get("llm_stream")
            use_async = self.config_dict.get("llm_gateway_config").get("llm_use_async")
            logger.info(f"Handling Gradio input: {user_input} | Stream: {stream}")
            try:
                response_gen = self.cognition_system.think(stimuli, tools=self.action_system.tools, stream=stream, use_async=use_async)
                
                async for chunk in response_gen:
                    if isinstance(chunk, str):
                        # For streaming chunks
                        await self.event_bus.emit('response.gradio', payload=chunk)
                    elif isinstance(chunk, Thought) or isinstance(chunk, Plan):
                        # For non-streaming responses
                        await self.event_bus.emit('response.gradio', payload=chunk.content if hasattr(chunk, 'content') else str(chunk))
                
                if stream:
                    await self.event_bus.emit('response.gradio', payload="<END_OF_RESPONSE>")
            except Exception as e:
                logger.error(f"Error in streaming response: {e}")
                await self.event_bus.emit('response.gradio', payload="An error occurred during response generation.")
                if stream:
                    await self.event_bus.emit('response.gradio', payload="<END_OF_RESPONSE>")

    # @staticmethod
    # def get_api_key(config_section: Dict[str, Any], key_field: str, env_var_field: str) -> Optional[str]:
    #     """
    #     Retrieve an API key from the configuration section.

    #     Args:
    #         config_section (Dict[str, Any]): The configuration section (e.g., embedder_config).
    #         key_field (str): The key in the config_section that may contain the API key directly.
    #         env_var_field (str): The key in the config_section that specifies the environment variable name.

    #     Returns:
    #         Optional[str]: The API key if found, else None.

    #     Raises:
    #         EnvironmentError: If the environment variable is specified but not set.
    #     """
    #     # Check if API key is provided directly
    #     api_key = config_section.get(key_field)
    #     if api_key:
    #         logger.info(f"Using provided API key for '{key_field}'.")
    #         return api_key

    #     # Else, check if an environment variable is specified
    #     env_var = config_section.get(env_var_field)
    #     if env_var:
    #         api_key = os.getenv(env_var)
    #         if api_key:
    #             logger.info(f"Retrieved API key for '{key_field}' from environment variable '{env_var}'.")
    #             return api_key
    #         else:
    #             logger.error(f"Environment variable '{env_var}' for '{key_field}' is not set.")
    #             raise EnvironmentError(f"Environment variable '{env_var}' for '{key_field}' is not set.")
        
    #     logger.warning(f"No API key provided for '{key_field}'.")
    #     return None