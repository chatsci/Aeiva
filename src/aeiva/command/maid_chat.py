# aeiva/commands/maid_chat.py

import os
import sys
import asyncio
import logging
import subprocess
import signal
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import click
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from aeiva.util.path_utils import get_project_root_dir
from aeiva.common.logger import setup_logging
from aeiva.command.command_utils import (
    get_package_root,
    get_log_dir,
    build_runtime,
)
from aeiva.command.gateway_registry import GatewayRegistry
from aeiva.util.file_utils import from_json_or_yaml
from aeiva.interface.gateway_base import GatewayBase


def _try_start_neo4j(logger):
    """Start Neo4j if NEO4J_HOME is set; return process or None."""
    neo4j_home = os.getenv("NEO4J_HOME")
    if not neo4j_home:
        logger.info("NEO4J_HOME not set — skipping Neo4j startup.")
        return None
    try:
        from aeiva.command.command_utils import validate_neo4j_home, start_neo4j
        validate_neo4j_home(logger, neo4j_home)
        return start_neo4j(logger, neo4j_home)
    except SystemExit:
        logger.warning("Neo4j validation failed — continuing without Neo4j.")
        return None
    except Exception as exc:
        logger.warning("Neo4j start failed (%s) — continuing without Neo4j.", exc)
        return None


def _try_stop_neo4j(logger, neo4j_process):
    if neo4j_process is None:
        return
    try:
        from aeiva.command.command_utils import stop_neo4j
        stop_neo4j(logger, neo4j_process)
    except Exception as exc:
        logger.warning("Neo4j stop failed: %s", exc)


class MaidChatGateway(GatewayBase[None]):
    def requires_route(self) -> bool:
        return False

# Define the request and response models
class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    response: str


def build_maid_app(
    *,
    config_dict: dict,
    runtime: Any,
    agent: Any,
    gateway_cfg: dict,
    raw_user_id: str,
    session_id: str,
    logger: logging.Logger,
    response_timeout: float,
    start_runtime: bool,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent = agent
        app.state.router = MaidChatGateway(
            gateway_cfg,
            agent.event_bus,
            response_timeout=response_timeout,
        )
        app.state.router.register_handlers()
        runtime_task = None
        if start_runtime:
            runtime_task = asyncio.create_task(
                runtime.run(raw_memory_session={"session_id": session_id, "user_id": raw_user_id})
            )
            logger.info("Agent runtime started.")
        try:
            yield
        finally:
            if start_runtime:
                logger.info("Shutting down the agent server.")
                runtime.request_stop()
                if runtime_task:
                    runtime_task.cancel()
                    await asyncio.gather(runtime_task, return_exceptions=True)

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/process_text", response_model=MessageResponse)
    async def process_text(request: MessageRequest):
        if not request.message:
            raise HTTPException(status_code=400, detail="No message provided")

        logger.info(f"Received message: {request.message}")

        try:
            meta = {"user_id": raw_user_id, "session_id": session_id}
            signal = app.state.router.build_input_signal(
                request.message,
                source="perception.maid",
                meta=meta,
            )
            response_text = await app.state.router.emit_input(
                signal,
                event_name="perception.stimuli",
                await_response=True,
            )
            logger.info(f"Agent response: {response_text}")
            return MessageResponse(response=response_text)
        except asyncio.TimeoutError:
            logger.error("Timed out waiting for agent response.")
            raise HTTPException(status_code=504, detail="Timeout waiting for agent response")
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    return app


def start_unity_app(maid_home: str, logger: logging.Logger) -> Optional[subprocess.Popen]:
    """
    Starts the Unity application.

    Args:
        maid_home (str): Path to the Unity application executable.
        logger (logging.Logger): Logger instance.

    Returns:
        Optional[subprocess.Popen]: The subprocess running the Unity application, or None if failed.
    """
    try:
        unity_process = subprocess.Popen(
            [maid_home],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid  # Start the process in a new session
        )
        logger.info(f"Unity application started from {maid_home}.")
        click.echo(f"Unity application started from {maid_home}.")
        return unity_process
    except FileNotFoundError:
        logger.error(f"Unity application not found at {maid_home}.")
        click.echo(f"Error: Unity application not found at {maid_home}.")
        return None
    except Exception as e:
        logger.error(f"Failed to start Unity application: {e}")
        click.echo(f"Error: Failed to start Unity application: {e}.")
        return None

def stop_unity_app(unity_process: subprocess.Popen, logger: logging.Logger):
    """
    Stops the Unity application gracefully.

    Args:
        unity_process (subprocess.Popen): The subprocess running the Unity application.
        logger (logging.Logger): Logger instance.
    """
    try:
        os.killpg(os.getpgid(unity_process.pid), signal.SIGTERM)
        unity_process.wait(timeout=10)
        logger.info("Unity application terminated gracefully.")
        click.echo("Unity application terminated gracefully.")
    except Exception as e:
        logger.error(f"Error terminating Unity application: {e}")
        click.echo(f"Error: Failed to terminate Unity application: {e}.")

@click.command(name="maid-chat")
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
    Starts the Aeiva Agent Server and launches the Unity application.
    """
    # Setup logging
    project_root = get_project_root_dir()
    logger_config_path = project_root / "configs" / "logger_config.yaml"
    logger_file_path = get_log_dir() / 'maid-chat.log'
    logger = setup_logging(
        config_file_path=logger_config_path,
        log_file_path=logger_file_path,
        verbose=verbose
    )
    
    # Load configuration
    if config is None:
        PACKAGE_ROOT = get_package_root()
        config_path = PACKAGE_ROOT / 'configs' / 'agent_config.yaml'
    else:
        config_path = Path(config)
    
    logger.info(f"Loading configuration from {config_path}")
    config_dict = from_json_or_yaml(config_path)
    agent_cfg = config_dict.get("agent_config") or {}
    agent_cfg["ui_enabled"] = False
    config_dict["agent_config"] = agent_cfg

    raw_memory_cfg = config_dict.get("raw_memory_config") or {}
    raw_user_id = str(raw_memory_cfg.get("user_id", "user"))
    session_id = uuid4().hex
    
    # Optionally start Neo4j
    neo4j_process = _try_start_neo4j(logger)
    
    # Initialize the Agent or MAS
    try:
        runtime, agent = build_runtime(config_dict)
        logger.info("Agent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Agent: {e}")
        click.echo(f"Error: Failed to initialize Agent: {e}")
        _try_stop_neo4j(logger, neo4j_process)
        sys.exit(1)
    
    # Read MAID_HOME environment variable
    maid_home = os.getenv('MAID_HOME')
    if not maid_home:
        logger.error("MAID_HOME environment variable is not set.")
        click.echo("Error: MAID_HOME environment variable is not set.")
        _try_stop_neo4j(logger, neo4j_process)
        sys.exit(1)
    
    maid_home_path = Path(maid_home)
    if not maid_home_path.exists():
        logger.error(f"Unity application not found at MAID_HOME: {maid_home}")
        click.echo(f"Error: Unity application not found at MAID_HOME: {maid_home}")
        _try_stop_neo4j(logger, neo4j_process)
        sys.exit(1)
    
    # Start the Unity application
    unity_process = start_unity_app(str(maid_home_path), logger)
    if unity_process is None:
        _try_stop_neo4j(logger, neo4j_process)
        sys.exit(1)
    
    registry = GatewayRegistry(config_dict)
    maid_gateway_cfg = registry.resolve_channel_config("maid")
    response_timeout = float(
        (config_dict.get("llm_gateway_config") or {}).get("llm_timeout", 60)
    )
    app = build_maid_app(
        config_dict=config_dict,
        runtime=runtime,
        agent=agent,
        gateway_cfg=maid_gateway_cfg,
        raw_user_id=raw_user_id,
        session_id=session_id,
        logger=logger,
        response_timeout=response_timeout,
        start_runtime=True,
    )
    
    # Run the FastAPI app using Uvicorn
    try:
        logger.info(f"Starting server at http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        logger.error(f"Server encountered an error: {e}")
        sys.exit(1)
    finally:
        _try_stop_neo4j(logger, neo4j_process)
        stop_unity_app(unity_process, logger)
        logger.info("Server has been stopped.")
