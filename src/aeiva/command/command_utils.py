"""
Here we put util functions related to database, logging and so on for different aeiva commands execution.
"""

import os
import sys
import logging
import subprocess
import signal
from pathlib import Path
import click
import importlib.resources as importlib_resources
from aeiva.logger.logger import get_logger


def get_package_root():
    """
    Determines the root path of the 'aeiva' package.
    """
    aeiva_path = Path(importlib_resources.files("aeiva"))
    package_root = aeiva_path.parents[1]
    return package_root.resolve()

def get_log_dir():
    """
    Determines a suitable path for the log file.
    Logs are stored in the user's home directory under '.aeiva/logs/'.
    """
    home_dir = Path.home()
    log_dir = home_dir / '.aeiva' / 'logs'  # Log saved to `~/.aeiva/logs/`
    log_dir.mkdir(parents=True, exist_ok=True)  # Ensure the log directory exists
    return log_dir

def setup_logging(log_file, verbose=False):
    """
    Sets up logging to both file and console.
    """
    logger = get_logger(__name__, level="DEBUG" if verbose else "INFO")

    # Create a file handler
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def validate_neo4j_home(logger, neo4j_home):
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

def start_neo4j(logger, neo4j_home):
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
        click.echo("Neo4j database started successfully.")
        return neo4j_process
    except FileNotFoundError:
        logger.error(f"Neo4j executable not found in {neo4j_command}.")
        click.echo(f"Error: Neo4j executable not found in {neo4j_command}.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start Neo4j: {e}")
        click.echo(f"Error: Failed to start Neo4j: {e}")
        sys.exit(1)

def stop_neo4j(logger, neo4j_process):
    """
    Stops the Neo4j database subprocess gracefully.
    """
    try:
        # Check if the process is still running
        if neo4j_process.poll() is None:
            os.killpg(os.getpgid(neo4j_process.pid), signal.SIGINT)  # Send SIGINT for graceful shutdown
            logger.info("Sent SIGINT to Neo4j subprocess.")
            click.echo("Shutting down Neo4j...")
            neo4j_process.wait(timeout=15)  # Increased timeout to 15 seconds
            logger.info("Neo4j database stopped successfully.")
            click.echo("Neo4j database stopped successfully.")
        else:
            logger.warning("Neo4j subprocess is already terminated.")
            click.echo("Warning: Neo4j subprocess is already terminated.")
    except subprocess.TimeoutExpired:
        logger.error("Neo4j did not terminate within the timeout period.")
        click.echo("Error: Neo4j did not terminate within the timeout period.")
        # Optionally, force kill
        try:
            os.killpg(os.getpgid(neo4j_process.pid), signal.SIGKILL)
            neo4j_process.wait(timeout=5)
            logger.info("Neo4j database forcefully terminated.")
            click.echo("Neo4j database forcefully terminated.")
        except Exception as e:
            logger.error(f"Failed to forcefully terminate Neo4j: {e}")
            click.echo(f"Error: Failed to forcefully terminate Neo4j: {e}")
    except ProcessLookupError:
        logger.warning("Neo4j subprocess does not exist.")
        click.echo("Warning: Neo4j subprocess does not exist. It may have already terminated.")
    except Exception as e:
        logger.error(f"Error stopping Neo4j: {e}")
        click.echo(f"Error: Failed to stop Neo4j: {e}")

def handle_exit(signum, frame, logger, neo4j_process):
    """
    Handles termination signals to ensure Neo4j is stopped gracefully.
    """
    logger.info(f"Received signal {signum}. Shutting down Neo4j.")
    click.echo(f"\nReceived signal {signum}. Shutting down Neo4j.")
    stop_neo4j(logger, neo4j_process)
    sys.exit(0)
