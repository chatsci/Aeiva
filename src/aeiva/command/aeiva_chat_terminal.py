"""
We can run the command like below: (specify your own config file path)
> aeiva-chat-terminal --config configs/agent_config.yaml
"""
import sys
import signal
import asyncio
from pathlib import Path
from uuid import uuid4
import click
from aeiva.util.file_utils import from_json_or_yaml
from aeiva.command.command_utils import (
    get_package_root,
    build_runtime_async,
    setup_command_logger,
)

# Get default agent config file path (prefer JSON if available)
PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / 'configs' / 'agent_config.json'
_yaml_config = PACKAGE_ROOT / 'configs' / 'agent_config.yaml'
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config

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
    logger = setup_command_logger(
        log_filename="aeiva-chat-terminal.log",
        verbose=verbose,
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
    
    raw_memory_cfg = config_data.get("raw_memory_config") or {}
    raw_user_id = str(raw_memory_cfg.get("user_id", "user"))
    session_payload = {"session_id": uuid4().hex, "user_id": raw_user_id}

    # Disable agent UI output for terminal mode (use TerminalGateway instead)
    agent_cfg = config_data.setdefault("agent_config", {})
    agent_cfg["ui_enabled"] = False

    # Avoid competing terminal readers when terminal gateway is enabled.
    perception_cfg = config_data.get("perception_config") or {}
    sensors = perception_cfg.get("sensors")
    if isinstance(sensors, list):
        perception_cfg["sensors"] = [
            sensor for sensor in sensors
            if (sensor or {}).get("sensor_name") != "percept_terminal_input"
        ]
        config_data["perception_config"] = perception_cfg

    # Start the Agent or MAS
    try:
        async def _main():
            runtime, agent = await build_runtime_async(config_data)

            from aeiva.interface.terminal_gateway import TerminalGateway

            terminal_cfg = config_data.get("terminal_config") or {}
            agent_cfg = config_data.get("agent_config") or {}
            terminal_cfg.setdefault("show_emotion", agent_cfg.get("show_emotion", False))
            terminal_gateway = TerminalGateway(terminal_cfg, agent.event_bus)
            await terminal_gateway.setup()

            stop_event = asyncio.Event()

            def _handle_sig(signum, frame):
                logger.info(f"Received signal {signum}. Stopping terminal gateway.")
                runtime.request_stop()
                terminal_gateway.request_stop()
                stop_event.set()

            # Register signal handlers to ensure clean shutdown
            signal.signal(signal.SIGINT, _handle_sig)
            signal.signal(signal.SIGTERM, _handle_sig)

            tasks = [
                asyncio.create_task(runtime.run(raw_memory_session=session_payload)),
                asyncio.create_task(terminal_gateway.run()),
                asyncio.create_task(stop_event.wait()),
            ]

            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            stop_event.set()
            runtime.request_stop()
            terminal_gateway.request_stop()

            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

        asyncio.run(_main())
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
        
        logger.info("Cleanup completed.")

if __name__ == "__main__":
    run()
