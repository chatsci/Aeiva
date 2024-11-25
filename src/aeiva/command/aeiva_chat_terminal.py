"""
We can run the command like below: (specify your own config file path)
> aeiva-chat-terminal --config configs/agent_config.yaml
"""
import os
import sys
import signal
import asyncio
from pathlib import Path
import click
from aeiva.agent.agent import Agent
from aeiva.util.file_utils import from_json_or_yaml
from aeiva.command.command_utils import (
    get_package_root,
    get_log_dir,
    setup_logging,
    validate_neo4j_home,
    start_neo4j,
    stop_neo4j,
    handle_exit,
)

# Get default agent config file path
PACKAGE_ROOT = get_package_root()
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / 'configs' / 'agent_config.yaml'

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
    logger = setup_logging(DEFAULT_LOG_PATH, verbose)
    
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
    
    # Register signal handlers to ensure Neo4j stops gracefully
    signal.signal(signal.SIGINT, lambda s, f: handle_exit(s, f, neo4j_process))
    signal.signal(signal.SIGTERM, lambda s, f: handle_exit(s, f, neo4j_process))
    
    # Start the Agent
    try:
        agent = Agent(config_data)
        agent.setup()
        asyncio.run(agent.run())
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