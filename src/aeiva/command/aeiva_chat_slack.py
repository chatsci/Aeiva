"""
Run Aeiva with Slack Socket Mode gateway.

> aeiva-chat-slack --config configs/agent_config.yaml
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
from aeiva.interface.slack_gateway import SlackGateway
from aeiva.util.file_utils import from_json_or_yaml


PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / "configs" / "agent_config.json"
_yaml_config = PACKAGE_ROOT / "configs" / "agent_config.yaml"
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config

LOGS_DIR = get_log_dir()
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_PATH = LOGS_DIR / "aeiva-chat-slack.log"


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
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def run(config, verbose):
    """
    Starts the Aeiva Slack gateway with the provided configuration.
    """
    project_root = PACKAGE_ROOT
    logger_config_path = project_root / "configs" / "logger_config.yaml"
    log_file_path = DEFAULT_LOG_PATH
    if not os.access(LOGS_DIR, os.W_OK):
        fallback_dir = project_root / "logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = fallback_dir / "aeiva-chat-slack.log"
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

    slack_cfg = config_dict.get("slack_config") or {}
    if not slack_cfg.get("enabled", False):
        click.echo("Error: slack_config.enabled is false. Enable Slack in config first.")
        sys.exit(1)

    # Disable terminal UI for Slack mode
    agent_cfg = config_dict.get("agent_config") or {}
    agent_cfg["ui_enabled"] = False
    config_dict["agent_config"] = agent_cfg

    neo4j_process = _try_start_neo4j(logger)

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
        _try_stop_neo4j(logger, neo4j_process)
        logger.info("Cleanup completed.")


if __name__ == "__main__":
    run()
