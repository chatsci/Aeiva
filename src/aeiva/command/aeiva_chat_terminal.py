"""
We can run the command like below: (specify your own config file path)
> aeiva-chat-terminal --config configs/agent_config.yaml
"""
import os
import sys
import signal
import asyncio
from pathlib import Path
from uuid import uuid4
import click
from aeiva.util.file_utils import from_json_or_yaml
from aeiva.util.path_utils import get_project_root_dir
from aeiva.common.logger import setup_logging
from aeiva.command.command_utils import (
    get_package_root,
    get_log_dir,
    validate_neo4j_home,
    start_neo4j,
    stop_neo4j,
    handle_exit,
    build_runtime,
)
import logging

# Get default agent config file path (prefer JSON if available)
PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / 'configs' / 'agent_config.json'
_yaml_config = PACKAGE_ROOT / 'configs' / 'agent_config.yaml'
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config

# Get default log file path
LOGS_DIR = get_log_dir()
LOGS_DIR.mkdir(parents=True, exist_ok=True)  # Ensure the log directory exists
DEFAULT_LOG_PATH = LOGS_DIR / 'aeiva-chat-terminal.log'


@click.command()
@click.option('--config', '-c', default=str(DEFAULT_CONFIG_PATH),
              help='Path to the configuration file (YAML or JSON).',
              type=click.Path(exists=True, dir_okay=False))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging.')
def run(config, verbose):
    """
    Starts the Aeiva chat terminal with the provided configuration.
    """
    # Setup logging
    project_root = get_project_root_dir()
    logger_config_path = project_root / "configs" / "logger_config.yaml"
    log_file_path = DEFAULT_LOG_PATH
    if not os.access(LOGS_DIR, os.W_OK):
        fallback_dir = project_root / "logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = fallback_dir / "aeiva-chat-terminal.log"
    logger = setup_logging(
        config_file_path=logger_config_path,
        log_file_path=log_file_path,
        verbose=verbose
    )
    
    click.echo(f"Loading configuration from {config}")
    config_path = Path(config)
    
    # Parse the configuration file with error handling
    try:
        config_data = from_json_or_yaml(config_path)
    except Exception as e:
        logger.error(f"Failed to parse configuration file: {e}")
        click.echo(f"Error: Failed to parse configuration file: {e}")
        sys.exit(1)
    
    # Retrieve NEO4J_HOME from environment variables
    neo4j_home = os.getenv('NEO4J_HOME')
    if not neo4j_home:
        logger.error("NEO4J_HOME is not set in the environment.")
        click.echo("Error: NEO4J_HOME is not set in the environment. Please set it in your shell configuration (e.g., .bashrc or .zshrc).")
        sys.exit(1)
    
    # Validate NEO4J_HOME path
    validate_neo4j_home(logger, neo4j_home)
    
    # Start Neo4j
    neo4j_process = start_neo4j(logger, neo4j_home)
    
    raw_memory_cfg = config_data.get("raw_memory_config") or {}
    raw_user_id = str(raw_memory_cfg.get("user_id", "user"))
    session_payload = {"session_id": uuid4().hex, "user_id": raw_user_id}

    # Start the Agent or MAS
    try:
        runtime, agent = build_runtime(config_data)

        def _handle_sig(signum, frame):
            logger.info(f"Received signal {signum}. Stopping agent.")
            runtime.request_stop()

        # Register signal handlers to ensure clean shutdown
        signal.signal(signal.SIGINT, _handle_sig)
        signal.signal(signal.SIGTERM, _handle_sig)

        asyncio.run(runtime.run(raw_memory_session=session_payload))
    except KeyboardInterrupt:
        logger.info("Agent execution interrupted by user.")
        click.echo("\nAgent execution interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}")
        click.echo(f"An error occurred during agent execution: {e}")
    finally:
        # # Perform any necessary cleanup
        # try:
        #     agent.cognition_components['memory'].delete_all()
        #     logger.info("All memory units deleted during cleanup.")
        # except NotImplementedError as nie:
        #     logger.warning(f"Delete All feature not implemented: {nie}")
        # except Exception as e:
        #     logger.error(f"Error during cleanup: {e}")
        #     click.echo("Failed to delete all memory units.")
        
        # Stop Neo4j
        stop_neo4j(logger, neo4j_process)
        logger.info("Cleanup completed.")

if __name__ == "__main__":
    run()
