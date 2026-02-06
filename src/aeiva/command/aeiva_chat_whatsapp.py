"""
Run Aeiva with WhatsApp Cloud API gateway.

> aeiva-chat-whatsapp --config configs/agent_config.yaml --port 8080

Requires a public URL (e.g. ngrok) for Meta webhook delivery.
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
from aeiva.interface.whatsapp_gateway import WhatsAppGateway
from aeiva.util.file_utils import from_json_or_yaml


PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / "configs" / "agent_config.json"
_yaml_config = PACKAGE_ROOT / "configs" / "agent_config.yaml"
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config


@click.command()
@click.option("--config", "-c", default=str(DEFAULT_CONFIG_PATH),
              help="Path to the configuration file (YAML or JSON).",
              type=click.Path(exists=True, dir_okay=False))
@click.option("--host", "-H", default="0.0.0.0",
              help="Host address for the webhook server.", show_default=True)
@click.option("--port", "-p", default=8080,
              help="Port for the webhook server.", show_default=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def run(config, host, port, verbose):
    """
    Starts the Aeiva WhatsApp gateway with the provided configuration.
    """
    logger = setup_command_logger(
        log_filename="aeiva-chat-whatsapp.log",
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
    wa_cfg = registry.resolve_channel_config("whatsapp")
    if not wa_cfg.get("enabled", False):
        click.echo("Error: whatsapp_config.enabled is false. Enable WhatsApp in config first.")
        sys.exit(1)

    # Disable terminal UI for WhatsApp mode
    agent_cfg = config_dict.get("agent_config") or {}
    agent_cfg["ui_enabled"] = False
    config_dict["agent_config"] = agent_cfg

    try:
        runtime, agent = build_runtime(config_dict)
        wa_gateway = WhatsAppGateway(wa_cfg, agent.event_bus)

        def _handle_sig(signum, frame):
            logger.info(f"Received signal {signum}. Stopping runtime.")
            runtime.request_stop()
            wa_gateway.request_stop()

        signal.signal(signal.SIGINT, _handle_sig)
        signal.signal(signal.SIGTERM, _handle_sig)

        async def _main():
            await wa_gateway.setup()
            runtime_task = asyncio.create_task(runtime.run())
            wa_task = asyncio.create_task(wa_gateway.run(host=host, port=port))
            done, pending = await asyncio.wait(
                [runtime_task, wa_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            runtime.request_stop()
            wa_gateway.request_stop()
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            return done

        click.echo(f"Starting Aeiva WhatsApp gateway on {host}:{port}...")
        asyncio.run(_main())
    except Exception as exc:
        logger.error(f"Error running WhatsApp gateway: {exc}")
        click.echo(f"Error: {exc}")
    finally:
        logger.info("Cleanup completed.")


if __name__ == "__main__":
    run()
