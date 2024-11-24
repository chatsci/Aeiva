import asyncio
import logging
import subprocess
import os
import sys
import signal
from pathlib import Path
import click
import importlib.resources as importlib_resources  # Correct import alias
from aeiva.agent.agent import Agent
from aeiva.util.file_utils import from_json_or_yaml

# Get default config file path
PACKAGE_NAME = 'aeiva'
def get_package_root():
    """
    Determines the root path of the 'aeiva' package.
    """
    package_root = Path(importlib_resources.files(PACKAGE_NAME))
    return package_root.resolve()
PACKAGE_ROOT = get_package_root()
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / 'configs' / 'agent_config.yaml'

# Get default log file path
LOGS_SUBDIR = 'logs'
DEFAULT_LOG_FILE = 'aeiva-chat-terminal.log'
def get_log_path():
    """
    Determines a suitable path for the log file.
    Logs are stored in the user's home directory under '.aeiva/logs/'.
    """
    home_dir = Path.home()
    log_dir = home_dir / '.aeiva' / LOGS_SUBDIR  # NOTE: the log is saved to `~/.aeiva/logs/`
    log_dir.mkdir(parents=True, exist_ok=True)  # Ensure the log directory exists
    return log_dir / DEFAULT_LOG_FILE
DEFAULT_LOG_PATH = get_log_path()

def setup_logging(log_path):
    """
    Configures logging to write to a file and suppress console output.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create a file handler
    file_handler = logging.FileHandler(log_path, mode='a')
    file_handler.setLevel(logging.INFO)

    # Create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)

    # Add a NullHandler to prevent logs from propagating to the console
    logger.addHandler(logging.NullHandler())

    return logger

logger = setup_logging(DEFAULT_LOG_PATH)

def validate_neo4j_home(neo4j_home):
    """
    Validates that the NEO4J_HOME path exists and contains the Neo4j executable.
    """
    if not os.path.isdir(neo4j_home):
        logger.error(f"NEO4J_HOME path does not exist or is not a directory: {neo4j_home}")
        click.echo(f"Error: NEO4J_HOME path does not exist or is not a directory: {neo4j_home}")
        sys.exit(1)
    
    neo4j_executable = os.path.join(neo4j_home, 'bin', 'neo4j')
    if not os.path.isfile(neo4j_executable) or not os.access(neo4j_executable, os.X_OK):
        logger.error(f"Neo4j executable not found or not executable at: {neo4j_executable}")
        click.echo(f"Error: Neo4j executable not found or not executable at: {neo4j_executable}")
        sys.exit(1)

def start_neo4j(neo4j_home):
    """
    Starts the Neo4j database as a subprocess.
    """
    neo4j_command = [os.path.join(neo4j_home, 'bin', 'neo4j'), 'console']
    try:
        neo4j_process = subprocess.Popen(
            neo4j_command,
            stdout=subprocess.DEVNULL,  # Suppress stdout
            stderr=subprocess.DEVNULL,  # Suppress stderr
            stdin=subprocess.DEVNULL,   # Prevent Neo4j from waiting for input
            preexec_fn=os.setsid       # Start the process in a new session
        )
        logger.info("Neo4j database started successfully.")
        return neo4j_process
    except FileNotFoundError:
        logger.error(f"Neo4j executable not found in {neo4j_command}.")
        click.echo(f"Error: Neo4j executable not found in {neo4j_command}.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start Neo4j: {e}")
        click.echo(f"Error: Failed to start Neo4j: {e}")
        sys.exit(1)

def stop_neo4j(neo4j_process):
    """
    Stops the Neo4j database subprocess gracefully.
    """
    try:
        # Check if the process is still running
        if neo4j_process.poll() is None:
            os.killpg(os.getpgid(neo4j_process.pid), signal.SIGINT)  # Send SIGINT for graceful shutdown
            logger.info("Sent SIGINT to Neo4j subprocess.")
            neo4j_process.wait(timeout=15)  # Increased timeout to 15 seconds
            logger.info("Neo4j database stopped successfully.")
        else:
            logger.warning("Neo4j subprocess is already terminated.")
    except subprocess.TimeoutExpired:
        logger.error("Neo4j did not terminate within the timeout period.")
        click.echo("Error: Neo4j did not terminate within the timeout period.")
        # Optionally, force kill
        try:
            os.killpg(os.getpgid(neo4j_process.pid), signal.SIGKILL)
            neo4j_process.wait(timeout=5)
            logger.info("Neo4j database forcefully terminated.")
        except Exception as e:
            logger.error(f"Failed to forcefully terminate Neo4j: {e}")
            click.echo(f"Error: Failed to forcefully terminate Neo4j: {e}")
    except ProcessLookupError:
        logger.warning("Neo4j subprocess does not exist.")
    except Exception as e:
        logger.error(f"Error stopping Neo4j: {e}")
        click.echo(f"Error: Failed to stop Neo4j: {e}")

def handle_exit(signum, frame, neo4j_process):
    """
    Handles termination signals to ensure Neo4j is stopped gracefully.
    """
    logger.info(f"Received signal {signum}. Shutting down Neo4j.")
    click.echo(f"\nReceived signal {signum}. Shutting down Neo4j.")
    stop_neo4j(neo4j_process)
    sys.exit(0)

@click.command()
@click.option('--config', '-c', default=str(DEFAULT_CONFIG_PATH),
              help='Path to the configuration file (YAML or JSON).',
              type=click.Path(exists=True, dir_okay=False))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging.')
def run(config, verbose):
    """
    Starts the Aeiva chat terminal with the provided configuration.
    """
    # Adjust logging level based on verbosity
    if verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        click.echo("Verbose logging enabled.")
    else:
        logger.setLevel(logging.INFO)
        for handler in logger.handlers:
            handler.setLevel(logging.INFO)
    
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
    validate_neo4j_home(neo4j_home)
    
    # Start Neo4j
    neo4j_process = start_neo4j(neo4j_home)
    
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
        stop_neo4j(neo4j_process)
        logger.info("Cleanup completed.")

if __name__ == "__main__":
    run()