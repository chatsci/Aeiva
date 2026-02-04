"""
Here we put util functions related to database, logging and so on for different aeiva commands execution.
"""

import os
import sys
import subprocess
import signal
from pathlib import Path
import click
import importlib.resources as importlib_resources
from typing import Any, Dict


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
    global _neo4j_stop_called
    if _neo4j_stop_called:
        return
    _neo4j_stop_called = True

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
    if _neo4j_stop_called:
        return
    logger.info(f"Received signal {signum}. Shutting down Neo4j.")
    click.echo(f"\nReceived signal {signum}. Shutting down Neo4j.")
    stop_neo4j(logger, neo4j_process)
    sys.exit(0)
_neo4j_stop_called = False


def resolve_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve *_env_var keys in a config dict by pulling from os.environ.

    Example:
        {"llm_api_key_env_var": "OPENAI_API_KEY"} -> {"llm_api_key": "..."}
    """
    def _resolve_mapping(mapping: Dict[str, Any]) -> None:
        for key, value in list(mapping.items()):
            if isinstance(value, dict):
                _resolve_mapping(value)
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _resolve_mapping(item)
                continue
            if not isinstance(value, str):
                continue
            if not key.endswith("_env_var"):
                continue
            target_key = key[: -len("_env_var")]
            if mapping.get(target_key):
                continue
            env_value = os.getenv(value)
            if env_value:
                mapping[target_key] = env_value

    if isinstance(config_dict, dict):
        _resolve_mapping(config_dict)
        _load_llm_api_key(config_dict)
    return config_dict


def _load_llm_api_key(config_dict: Dict[str, Any]) -> None:
    llm_cfg = config_dict.get("llm_gateway_config")
    if not isinstance(llm_cfg, dict):
        return
    if llm_cfg.get("llm_api_key"):
        return
    cfg_path = get_package_root() / "configs" / "llm_api_keys.yaml"
    if not cfg_path.exists():
        return
    try:
        import yaml
        keys = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return
    api_key = keys.get("openai_api_key")
    if api_key:
        llm_cfg["llm_api_key"] = api_key


def build_runtime(config_dict: Dict[str, Any]):
    """
    Build either a single Agent or a MultiAgentSystem based on config.

    Returns:
        (runtime, main_agent)
    """
    from aeiva.agent.agent import Agent
    resolve_env_vars(config_dict)
    from aeiva.host.host_router import configure_host_router
    from aeiva.tool.registry import set_tool_router
    router = configure_host_router(config_dict)
    if router:
        set_tool_router(router)
    mas_cfg = config_dict.get("mas_config") or {}
    if mas_cfg.get("enabled"):
        from aeiva.mas import MultiAgentSystem
        runtime = MultiAgentSystem(config_dict)
        runtime.setup()
        return runtime, runtime.main_agent

    agent = Agent(config_dict)
    agent.setup()
    return agent, agent


async def build_runtime_async(config_dict: Dict[str, Any]):
    """
    Build either a single Agent or a MultiAgentSystem asynchronously.

    Returns:
        (runtime, main_agent)
    """
    from aeiva.agent.agent import Agent
    resolve_env_vars(config_dict)
    from aeiva.host.host_router import configure_host_router
    from aeiva.tool.registry import set_tool_router
    router = configure_host_router(config_dict)
    if router:
        set_tool_router(router)
    mas_cfg = config_dict.get("mas_config") or {}
    if mas_cfg.get("enabled"):
        from aeiva.mas import MultiAgentSystem
        runtime = MultiAgentSystem(config_dict)
        await runtime.setup_async()
        return runtime, runtime.main_agent

    agent = Agent(config_dict)
    await agent.setup_async()
    return agent, agent
