"""
Unified Gateway: run multiple channels against shared or dedicated gateway contexts.

> aeiva-gateway --config configs/agent_config.yaml
"""
from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import click

from aeiva.common.logger import setup_logging
from aeiva.command.command_utils import get_log_dir, get_package_root, build_runtime_async, resolve_env_vars
from aeiva.command.gateway_registry import GatewayRegistry
from aeiva.interface.slack_gateway import SlackGateway
from aeiva.interface.terminal_gateway import TerminalGateway
from aeiva.interface.whatsapp_gateway import WhatsAppGateway
from aeiva.event.event_names import EventNames
from aeiva.util.file_utils import from_json_or_yaml

PACKAGE_ROOT = get_package_root()
_json_config = PACKAGE_ROOT / "configs" / "agent_config.json"
_yaml_config = PACKAGE_ROOT / "configs" / "agent_config.yaml"
DEFAULT_CONFIG_PATH = _json_config if _json_config.exists() else _yaml_config

LOGS_DIR = get_log_dir()
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_PATH = LOGS_DIR / "aeiva-gateway.log"


def _suppress_gradio_routes_print() -> None:
    try:
        import gradio.routes as gr_routes
        gr_routes.print = lambda *args, **kwargs: None
    except Exception:
        pass


@dataclass
class UvicornHandle:
    server: Any
    task: asyncio.Task

    def request_stop(self) -> None:
        self.server.should_exit = True


def _try_start_neo4j(logger):
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


@click.command(name="aeiva-gateway")
@click.option("--config", "-c", default=str(DEFAULT_CONFIG_PATH),
              help="Path to the configuration file (YAML or JSON).",
              type=click.Path(exists=True, dir_okay=False))
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def run(config, verbose):
    project_root = PACKAGE_ROOT
    logger_config_path = project_root / "configs" / "logger_config.yaml"
    log_file_path = DEFAULT_LOG_PATH
    if not os.access(LOGS_DIR, os.W_OK):
        fallback_dir = project_root / "logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = fallback_dir / "aeiva-gateway.log"
    logger = setup_logging(
        config_file_path=logger_config_path,
        log_file_path=log_file_path,
        verbose=verbose,
    )

    click.echo(f"Loading configuration from {config}")
    config_path = Path(config)
    config_dict = from_json_or_yaml(config_path)
    resolve_env_vars(config_dict)

    # Unified gateway shouldn't emit terminal UI output.
    agent_cfg = config_dict.setdefault("agent_config", {})
    agent_cfg["ui_enabled"] = False

    # Avoid competing terminal readers when terminal gateway is enabled.
    perception_cfg = config_dict.get("perception_config") or {}
    sensors = perception_cfg.get("sensors")
    if isinstance(sensors, list):
        perception_cfg["sensors"] = [
            sensor for sensor in sensors
            if (sensor or {}).get("sensor_name") != "percept_terminal_input"
        ]
        config_dict["perception_config"] = perception_cfg

    registry = GatewayRegistry(config_dict, runtime_builder=build_runtime_async)

    slack_cfg = registry.resolve_channel_config("slack")
    terminal_cfg = registry.resolve_channel_config("terminal")
    whatsapp_cfg = registry.resolve_channel_config("whatsapp")
    realtime_cfg = registry.resolve_channel_config("realtime")
    maid_cfg = registry.resolve_channel_config("maid")
    gradio_cfg = registry.resolve_channel_config("gradio")
    realtime_mode = (config_dict.get("realtime_config") or {}).get("mode", "turn_based")

    neo4j_process = _try_start_neo4j(logger)

    gateways: List[Any] = []
    runtime_tasks: List[asyncio.Task] = []
    gateway_tasks: List[asyncio.Task] = []
    uvicorn_handles: List[UvicornHandle] = []
    unity_processes: List[Any] = []
    stop_event = asyncio.Event()

    def _handle_sig(signum, frame):
        logger.info("Received signal %s. Stopping gateway.", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    async def _main():
        pending_gateways: List[tuple[str, Any, Dict[str, Any]]] = []

        if slack_cfg.get("enabled"):
            ctx = await registry.get_context_async("slack", slack_cfg)
            pending_gateways.append(("slack", ctx, slack_cfg))

        if terminal_cfg.get("enabled"):
            ctx = await registry.get_context_async("terminal", terminal_cfg)
            pending_gateways.append(("terminal", ctx, terminal_cfg))

        if whatsapp_cfg.get("enabled"):
            ctx = await registry.get_context_async("whatsapp", whatsapp_cfg)
            pending_gateways.append(("whatsapp", ctx, whatsapp_cfg))

        if realtime_cfg.get("enabled"):
            if realtime_mode != "turn_based":
                logger.warning("Realtime mode '%s' not supported in unified gateway. Skipping.", realtime_mode)
            else:
                ctx = await registry.get_context_async("realtime", realtime_cfg)
                pending_gateways.append(("realtime", ctx, realtime_cfg))

        if maid_cfg.get("enabled"):
            ctx = await registry.get_context_async("maid", maid_cfg)
            pending_gateways.append(("maid", ctx, maid_cfg))

        if gradio_cfg.get("enabled"):
            ctx = await registry.get_context_async("gradio", gradio_cfg)
            pending_gateways.append(("gradio", ctx, gradio_cfg))

        for ctx in registry.contexts.values():
            runtime_tasks.append(asyncio.create_task(ctx.runtime.run()))
            logger.info("Gateway runtime started (gateway_id=%s).", ctx.gateway_id)
            if ctx.agent and ctx.agent.event_bus:
                async def _stop_from_agent(event: Any, *, _gateway_id: str = ctx.gateway_id) -> None:
                    logger.info("Agent stop requested (gateway_id=%s).", _gateway_id)
                    stop_event.set()

                _stop_from_agent.__name__ = f"gateway_stop_from_{ctx.gateway_id}"
                ctx.agent.event_bus.subscribe(EventNames.AGENT_STOP, _stop_from_agent)

        for name, ctx, cfg in pending_gateways:
            if name == "slack":
                slack_gateway = SlackGateway(cfg, ctx.agent.event_bus)
                await slack_gateway.setup()
                gateways.append(slack_gateway)
                gateway_tasks.append(asyncio.create_task(slack_gateway.run()))
                logger.info("Slack gateway started (scope=%s).", cfg.get("gateway_scope"))
            elif name == "terminal":
                terminal_gateway = TerminalGateway(cfg, ctx.agent.event_bus)
                await terminal_gateway.setup()
                gateways.append(terminal_gateway)
                gateway_tasks.append(asyncio.create_task(terminal_gateway.run()))
                logger.info("Terminal gateway started (scope=%s).", cfg.get("gateway_scope"))
            elif name == "whatsapp":
                wa_gateway = WhatsAppGateway(cfg, ctx.agent.event_bus)
                await wa_gateway.setup()
                gateways.append(wa_gateway)
                host = cfg.get("host", "0.0.0.0")
                port = int(cfg.get("port", 8080))
                gateway_tasks.append(asyncio.create_task(wa_gateway.run(host=host, port=port)))
                logger.info("WhatsApp gateway started (scope=%s).", cfg.get("gateway_scope"))
            elif name == "realtime":
                from aeiva.command.aeiva_chat_realtime import build_turn_based_realtime_ui
                from aeiva.interface.gateway_base import ResponseQueueGateway
                import queue as sync_queue

                response_queue = sync_queue.Queue()
                response_timeout = float(
                    (config_dict.get("llm_gateway_config") or {}).get("llm_timeout", 60.0)
                )
                route_token = "realtime"
                queue_gateway = ResponseQueueGateway(
                    cfg,
                    ctx.agent.event_bus,
                    response_queue,
                    response_timeout=response_timeout,
                    require_route=True,
                )
                queue_gateway.register_handlers()
                demo, _handler = build_turn_based_realtime_ui(
                    config_dict=config_dict,
                    agent=ctx.agent,
                    queue_gateway=queue_gateway,
                    response_queue=response_queue,
                    log=logger,
                    route_token=route_token,
                )
                _suppress_gradio_routes_print()
                demo.launch(share=True, prevent_thread_lock=True)
                logger.info("Realtime Gradio UI launched (scope=%s).", cfg.get("gateway_scope"))
            elif name == "maid":
                from aeiva.command.maid_chat import build_maid_app, start_unity_app, stop_unity_app
                import uvicorn

                start_unity = bool(cfg.get("start_unity", True))
                if start_unity:
                    maid_home = os.getenv(cfg.get("maid_home_env", "MAID_HOME"))
                    if not maid_home:
                        raise RuntimeError("MAID_HOME is not set; cannot start maid gateway.")
                    unity_process = start_unity_app(maid_home, logger)
                    if unity_process is None:
                        raise RuntimeError("Failed to launch Unity app for maid gateway.")
                    unity_processes.append(unity_process)

                response_timeout = float(
                    (config_dict.get("llm_gateway_config") or {}).get("llm_timeout", 60)
                )
                raw_user_id = str(
                    (config_dict.get("raw_memory_config") or {}).get("user_id", "user")
                )
                app = build_maid_app(
                    config_dict=config_dict,
                    runtime=ctx.runtime,
                    agent=ctx.agent,
                    gateway_cfg=cfg,
                    raw_user_id=raw_user_id,
                    session_id=os.urandom(8).hex(),
                    logger=logger,
                    response_timeout=response_timeout,
                    start_runtime=False,
                )

                host = cfg.get("host", "0.0.0.0")
                port = int(cfg.get("port", 8000))
                server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="info"))
                task = asyncio.create_task(server.serve())
                uvicorn_handles.append(UvicornHandle(server=server, task=task))
                gateway_tasks.append(task)
                logger.info("Maid gateway started (scope=%s).", cfg.get("gateway_scope"))
            elif name == "gradio":
                from aeiva.command.aeiva_chat_gradio import build_gradio_chat_ui
                from aeiva.interface.gateway_base import ResponseQueueGateway
                import queue as sync_queue

                response_queue = sync_queue.Queue()
                response_timeout = float(
                    (config_dict.get("llm_gateway_config") or {}).get("llm_timeout", 60.0)
                )
                route_token = "gradio"
                queue_gateway = ResponseQueueGateway(
                    cfg,
                    ctx.agent.event_bus,
                    response_queue,
                    response_timeout=response_timeout,
                    require_route=True,
                )
                queue_gateway.register_handlers()
                demo = build_gradio_chat_ui(
                    config_dict=config_dict,
                    agent=ctx.agent,
                    queue_gateway=queue_gateway,
                    response_queue=response_queue,
                    log=logger,
                    route_token=route_token,
                )
                gradio_share = (config_dict.get("gradio_config") or {}).get("share", True)
                demo.launch(share=gradio_share, prevent_thread_lock=True)
                logger.info("Gradio chat UI launched (scope=%s).", cfg.get("gateway_scope"))

        if not runtime_tasks and not gateway_tasks:
            logger.warning("No gateways enabled. Exiting.")
            return

        wait_tasks = runtime_tasks + gateway_tasks + [asyncio.create_task(stop_event.wait())]
        done, pending = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)
        stop_event.set()

        for ctx in registry.contexts.values():
            ctx.request_stop()
        for gateway in gateways:
            gateway.request_stop()
        for handle in uvicorn_handles:
            handle.request_stop()
        if unity_processes:
            from aeiva.command.maid_chat import stop_unity_app
            for process in unity_processes:
                stop_unity_app(process, logger)

        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        return done

    try:
        asyncio.run(_main())
    finally:
        _try_stop_neo4j(logger, neo4j_process)
        logger.info("Gateway shutdown complete.")


if __name__ == "__main__":
    run()
