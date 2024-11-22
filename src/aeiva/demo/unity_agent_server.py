# agent.py

# You can run this script like below:
# uvicorn unity_agent_server:app --host 0.0.0.0 --port 8000 --reload


import os
import asyncio
import sys
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
from aeiva.event.event_bus import EventBus

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
        self.setup_event_handlers()

    def setup(self) -> None:
        """
        Set up all systems.
        """
        self.perception_system.setup()
        self.cognition_system.setup()
        self.action_system.setup()

    async def process_input(self, input_text: str) -> str:
        """
        Process input text and return the agent's response.
        """
        stimuli = Stimuli(signals=[Signal(data=input_text, modularity='text')])
        output = await self.cognition_system.think(stimuli, stream=False, tools=self.action_system.tools)

        # Return the response content
        return output.content

    def setup_event_handlers(self) -> None:
        """
        Set up event handlers for perception, cognition, and action events.
        """
        @self.event_bus.on('action.plan')
        async def handle_plan(event):
            plan = event.payload
            await self.action_system.execute(plan)

# server.py

import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

#from agent import Agent  # Import your Agent class
from aeiva.cognition.brain.llm_brain import LLMBrain
from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.cognition.input_interpreter.simple_input_interpreter import SimpleInputInterpreter
from aeiva.cognition.output_orchestrator.simple_output_orchestrator import SimpleOutputOrchestrator
from aeiva.cognition.memory.simple_memory import SimpleMemory
from aeiva.cognition.emotion.simple_emotion import SimpleEmotion
from aeiva.cognition.world_model.simple_world_model import SimpleWorldModel

import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the request model
class MessageRequest(BaseModel):
    message: str

# Define the response model
class MessageResponse(BaseModel):
    response: str

# Instantiate the agent when the application starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    try:
        # Define configurations
        perception_config = {
            "sensors": [
                # No need for terminal input sensor in FastAPI context
            ]
        }

        # Load environment variables and set up LLMBrain
        API_KEY = os.getenv('OPENAI_API_KEY')
        config = LLMGatewayConfig(
            llm_api_key=API_KEY,
            llm_model_name="gpt-4-turbo",
            llm_temperature=0.7,
            llm_max_output_tokens=1000,
            llm_stream=False
        )
        llm_brain = LLMBrain(config)
        cognition_components = {
            "input_interpreter": SimpleInputInterpreter(),
            "brain": llm_brain,
            "output_orchestrator": SimpleOutputOrchestrator(),
            "memory": SimpleMemory(),
            "emotion": SimpleEmotion(),
            "world_model": SimpleWorldModel(),
            "config": None
        }

        action_config = {
            "tools": [
                "play_music",
                "stop_music",
                "list_files",
                # Add other tools as needed
            ]
        }

        # Create agent instance
        agent = Agent(perception_config, cognition_components, action_config)
        agent.setup()
        # Attach the agent to the app state for access in routes
        app.state.agent = agent
        logger.info("Agent has been initialized and is ready to receive messages.")

        yield  # Control is transferred to the application

    finally:
        # Shutdown: Perform any necessary cleanup here
        logger.info("Shutting down the agent server.")
        # If the Agent class has a shutdown method, call it here
        if hasattr(app.state, 'agent'):
            # Example: await app.state.agent.shutdown()
            pass


app = FastAPI(lifespan=lifespan)

# Enable CORS for all origins (for development purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins; adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the endpoint
@app.post("/process_text", response_model=MessageResponse)
async def process_text(request: MessageRequest):
    if not request.message:
        raise HTTPException(status_code=400, detail="No message provided")
    
    print(f"Received message from Unity: {request.message}")

    # Process the message using the agent
    response_text = await agent.process_input(request.message)
    
    print(f"Agent response: {response_text}")

    return MessageResponse(response=response_text)