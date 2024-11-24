# agent.py

# You can run this script like below:
# uvicorn unity_agent_server:app --host 0.0.0.0 --port 8000 --reload

import os
import asyncio
import sys
from typing import Any
import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager


from aeiva.agent.agent import Agent
from aeiva.util.file_utils import from_json_or_yaml


import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize the Agent using the from_config class method
config_path = 'agent_config.yaml'  # Ensure this path is correct
config_dict = from_json_or_yaml(config_path)

try:
    agent = Agent(config_dict)
    agent.setup()
    logger.info("Agent initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Agent: {e}")
    agent = None


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