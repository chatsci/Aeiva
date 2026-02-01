"""
Run Aeiva with WhatsApp Cloud API gateway.

> aeiva-chat-whatsapp --config configs/agent_config.yaml --port 8080

Requires a public URL (e.g. ngrok) for Meta webhook delivery.
"""
import os
import sys
import signal
import asyncio
from pathlib import Path
import click

from aeiva.common.logger import setup_logging
from aeiva.command.command_utils import (
    get_package_root,
    get_log_dir,
    build_runtime,
)
from aeiva.interface.whatsapp_gateway import WhatsAppGateway
from aeiva.util.file_utils import from_json_or_yaml


PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / "configs" / "agent_config.json"
_yaml_config = PACKAGE_ROOT / "configs" / "agent_config.yaml"
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config

LOGS_DIR = get_log_dir()
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_PATH = LOGS_DIR / "aeiva-chat-whatsapp.log"


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
    project_root = PACKAGE_ROOT
    logger_config_path = project_root / "configs" / "logger_config.yaml"
    log_file_path = DEFAULT_LOG_PATH
    if not os.access(LOGS_DIR, os.W_OK):
        fallback_dir = project_root / "logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = fallback_dir / "aeiva-chat-whatsapp.log"
    logger = setup_logging(
        config_file_path=logger_config_path,
        log_file_path=log_file_path,
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

    wa_cfg = config_dict.get("whatsapp_config") or {}
    if not wa_cfg.get("enabled", False):
        click.echo("Error: whatsapp_config.enabled is false. Enable WhatsApp in config first.")
        sys.exit(1)

    # Disable terminal UI for WhatsApp mode
    agent_cfg = config_dict.get("agent_config") or {}
    agent_cfg["ui_enabled"] = False
    config_dict["agent_config"] = agent_cfg

    neo4j_process = _try_start_neo4j(logger)

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
        _try_stop_neo4j(logger, neo4j_process)
        logger.info("Cleanup completed.")


if __name__ == "__main__":
    run()
