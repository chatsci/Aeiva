# aeiva/commands/aeiva_server.py

import sys
from pathlib import Path

import click
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from aeiva.command.command_utils import (
    get_package_root,
    setup_command_logger,
    prepare_runtime_config,
)
from aeiva.agent.agent import Agent
from aeiva.util.file_utils import from_json_or_yaml

# Define the request and response models
class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    response: str

@click.command(name="aeiva-server")
@click.option(
    '--config', '-c',
    default=None,
    help='Path to the configuration file (YAML or JSON).',
    type=click.Path(exists=True, dir_okay=False)
)
@click.option(
    '--host', '-H',
    default="0.0.0.0",
    help='Host address to run the server on.',
    show_default=True
)
@click.option(
    '--port', '-p',
    default=8000,
    help='Port number to run the server on.',
    show_default=True
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging.'
)
def run(config, host, port, verbose):
    """
    Starts the Aeiva Agent Server using FastAPI.
    """
    # Setup logging
    project_root = get_package_root()
    logger = setup_command_logger(
        log_filename="aeiva-server.log",
        project_root=project_root,
        verbose=verbose,
    )
    
    # Load configuration
    if config is None:
        config_path = project_root / 'configs' / 'agent_config.yaml'
    else:
        config_path = Path(config)
    
    logger.info(f"Loading configuration from {config_path}")
    config_dict = from_json_or_yaml(config_path)
    prepare_runtime_config(config_dict)
    
    # Initialize the Agent
    try:
        agent = Agent(config_dict)
        agent.setup()
        logger.info("Agent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Agent: {e}")
        click.echo(f"Error: Failed to initialize Agent: {e}")
        sys.exit(1)
    
    # Define the FastAPI app with lifespan
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent = agent
        logger.info("Agent has been initialized and is ready to receive messages.")
        try:
            yield
        finally:
            logger.info("Shutting down the agent server.")
            # If the Agent class has a shutdown method, call it here
            if hasattr(app.state.agent, 'shutdown'):
                await app.state.agent.shutdown()
            logger.info("Agent server shut down gracefully.")
    
    app = FastAPI(lifespan=lifespan)
    
    # Enable CORS for all origins (for development purposes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Define the endpoint
    @app.post("/process_text", response_model=MessageResponse)
    async def process_text(request: MessageRequest):
        if not request.message:
            raise HTTPException(status_code=400, detail="No message provided")
        
        logger.info(f"Received message: {request.message}")
    
        # Process the message using the agent
        try:
            response_text = await app.state.agent.process_input(request.message)
            logger.info(f"Agent response: {response_text}")
            return MessageResponse(response=response_text)
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
    
    # Run the FastAPI app using Uvicorn
    try:
        logger.info(f"Starting server at http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        logger.error(f"Server encountered an error: {e}")
        sys.exit(1)
    finally:
        logger.info("Server has been stopped.")
