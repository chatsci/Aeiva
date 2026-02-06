"""
Run Aeiva with Slack Socket Mode gateway.

> aeiva-chat-slack --config configs/agent_config.yaml
"""
import sys
import signal
import asyncio
from pathlib import Path
import click

from aeiva.command.command_utils import (
    get_package_root,
    build_runtime,
    setup_command_logger,
)
from aeiva.command.gateway_registry import GatewayRegistry
from aeiva.interface.slack_gateway import SlackGateway
from aeiva.util.file_utils import from_json_or_yaml


PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / "configs" / "agent_config.json"
_yaml_config = PACKAGE_ROOT / "configs" / "agent_config.yaml"
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config


@click.command()
@click.option("--config", "-c", default=str(DEFAULT_CONFIG_PATH),
              help="Path to the configuration file (YAML or JSON).",
              type=click.Path(exists=True, dir_okay=False))
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def run(config, verbose):
    """
    Starts the Aeiva Slack gateway with the provided configuration.
    """
    logger = setup_command_logger(
        log_filename="aeiva-chat-slack.log",
        verbose=verbose,
    )

    click.echo(f"Loading configuration from {config}")
    config_path = Path(config)
    try:
        config_dict = from_json_or_yaml(config_path)
    except Exception as exc:
        logger.error(f"Failed to parse configuration file: {exc}")
        click.echo(f"Error: Failed to parse configuration file: {exc}")
        sys.exit(1)

    registry = GatewayRegistry(config_dict)
    slack_cfg = registry.resolve_channel_config("slack")
    if not slack_cfg.get("enabled", False):
        click.echo("Error: slack_config.enabled is false. Enable Slack in config first.")
        sys.exit(1)

    # Disable terminal UI for Slack mode
    agent_cfg = config_dict.get("agent_config") or {}
    agent_cfg["ui_enabled"] = False
    config_dict["agent_config"] = agent_cfg

    try:
        runtime, agent = build_runtime(config_dict)
        slack_gateway = SlackGateway(slack_cfg, agent.event_bus)

        def _handle_sig(signum, frame):
            logger.info(f"Received signal {signum}. Stopping runtime.")
            runtime.request_stop()
            slack_gateway.request_stop()

        signal.signal(signal.SIGINT, _handle_sig)
        signal.signal(signal.SIGTERM, _handle_sig)

        async def _main():
            await slack_gateway.setup()
            runtime_task = asyncio.create_task(runtime.run())
            slack_task = asyncio.create_task(slack_gateway.run())
            done, pending = await asyncio.wait(
                [runtime_task, slack_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            runtime.request_stop()
            slack_gateway.request_stop()
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            return done

        click.echo("Starting Aeiva Slack gateway...")
        asyncio.run(_main())
    except Exception as exc:
        logger.error(f"Error running Slack gateway: {exc}")
        click.echo(f"Error: {exc}")
    finally:
        logger.info("Cleanup completed.")


if __name__ == "__main__":
    run()
