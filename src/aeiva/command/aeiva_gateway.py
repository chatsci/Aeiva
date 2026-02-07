"""
Unified Gateway: run multiple channels against shared or dedicated gateway contexts.

> aeiva-gateway --config configs/agent_config.yaml
"""
from __future__ import annotations

import asyncio
import os
import secrets
import signal
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import click

from aeiva.command.command_utils import (
    get_log_dir,
    get_package_root,
    build_runtime_async,
    prepare_runtime_config,
    setup_command_logger,
)
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
DEFAULT_HOST_DAEMON_TOKEN_ENV = "AEIVA_HOST_DAEMON_TOKEN"


def _suppress_gradio_routes_print() -> None:
    try:
        import gradio.routes as gr_routes
        gr_routes.print = lambda *args, **kwargs: None
    except Exception:
        pass


def _as_non_empty_str(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _prepare_host_auth_for_autostart(
    logger: Any,
    host_cfg: Dict[str, Any],
    *,
    target_env: Dict[str, str],
) -> None:
    """
    Ensure daemon and routed host endpoints share a usable auth token.

    For `aeiva-gateway` auto-start mode, we provision an in-memory token when
    required auth is enabled but no token is configured. The token is injected
    into the daemon subprocess environment and mirrored to host endpoints in the
    runtime config so routed tool calls authenticate successfully.
    """
    daemon_cfg = host_cfg.get("daemon")
    if not isinstance(daemon_cfg, dict):
        daemon_cfg = {}
        host_cfg["daemon"] = daemon_cfg

    require_auth_raw = daemon_cfg.get("require_auth")
    require_auth = True if require_auth_raw is None else bool(require_auth_raw)
    if not require_auth:
        return

    raw_hosts = host_cfg.get("hosts")
    host_tokens: set[str] = set()
    if isinstance(raw_hosts, dict):
        for host_entry in raw_hosts.values():
            if not isinstance(host_entry, dict):
                continue
            token = _as_non_empty_str(host_entry.get("token"))
            if token:
                host_tokens.add(token)

    auth_env_var = (
        _as_non_empty_str(daemon_cfg.get("auth_token_env_var"))
        or DEFAULT_HOST_DAEMON_TOKEN_ENV
    )
    daemon_token = _as_non_empty_str(daemon_cfg.get("auth_token"))
    if not daemon_token:
        daemon_token = _as_non_empty_str(target_env.get(auth_env_var))
    if not daemon_token and len(host_tokens) == 1:
        daemon_token = next(iter(host_tokens))
    if not daemon_token:
        daemon_token = secrets.token_urlsafe(32)
        logger.info(
            "Generated ephemeral host daemon token for this gateway session (%s).",
            auth_env_var,
        )

    daemon_cfg["auth_token_env_var"] = auth_env_var
    daemon_cfg["auth_token"] = daemon_token
    target_env[auth_env_var] = daemon_token

    if isinstance(raw_hosts, dict):
        for host_name, host_entry in raw_hosts.items():
            if not isinstance(host_entry, dict):
                continue
            host_token = _as_non_empty_str(host_entry.get("token"))
            if host_token and host_token != daemon_token:
                logger.warning(
                    "Host '%s' token differs from daemon token; routed calls may fail auth.",
                    host_name,
                )
                continue
            if not host_token:
                host_entry["token"] = daemon_token


def _is_local_loopback_host(host: Optional[str]) -> bool:
    if not isinstance(host, str):
        return False
    normalized = host.strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def _is_tcp_port_available(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, int(port)))
        return True
    except OSError:
        return False


def _pick_free_tcp_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _rewrite_local_host_urls_for_port(
    host_cfg: Dict[str, Any],
    *,
    old_port: int,
    new_port: int,
) -> None:
    raw_hosts = host_cfg.get("hosts")
    if not isinstance(raw_hosts, dict):
        return

    for host_entry in raw_hosts.values():
        if not isinstance(host_entry, dict):
            continue
        url = _as_non_empty_str(host_entry.get("url"))
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not _is_local_loopback_host(parsed.hostname):
            continue
        if parsed.port != int(old_port):
            continue

        host_part = parsed.hostname or "127.0.0.1"
        if ":" in host_part and not host_part.startswith("["):
            host_part = f"[{host_part}]"
        netloc = f"{host_part}:{int(new_port)}"
        if parsed.username:
            auth = parsed.username
            if parsed.password:
                auth += f":{parsed.password}"
            netloc = f"{auth}@{netloc}"

        host_entry["url"] = urlunparse(parsed._replace(netloc=netloc))


def _resolve_autostart_daemon_port(
    logger: Any,
    host_cfg: Dict[str, Any],
    *,
    daemon_host: str,
    daemon_port: int,
) -> int:
    """Pick a daemon port, rebinding when configured local port is already in use."""
    if _is_tcp_port_available(daemon_host, daemon_port):
        return daemon_port

    try:
        new_port = _pick_free_tcp_port(daemon_host)
    except OSError:
        # Fallback for uncommon host strings where bind(host, 0) is not valid.
        new_port = _pick_free_tcp_port("127.0.0.1")

    logger.warning(
        "Host daemon port %s is already in use; rebinding auto-start daemon to %s.",
        daemon_port,
        new_port,
    )

    daemon_cfg = host_cfg.get("daemon")
    if isinstance(daemon_cfg, dict):
        daemon_cfg["port"] = new_port
    _rewrite_local_host_urls_for_port(
        host_cfg,
        old_port=daemon_port,
        new_port=new_port,
    )
    return new_port


@dataclass
class UvicornHandle:
    server: Any
    task: asyncio.Task

    def request_stop(self) -> None:
        self.server.should_exit = True


def _try_start_host(logger, config_dict, log_dir: Path, config_path: Optional[Path] = None):
    host_cfg = config_dict.get("host_config") or {}
    if not host_cfg.get("enabled"):
        return None
    if not host_cfg.get("auto_start"):
        return None

    startup_env = os.environ.copy()
    _prepare_host_auth_for_autostart(logger, host_cfg, target_env=startup_env)

    daemon_cfg = host_cfg.get("daemon") or {}
    host = daemon_cfg.get("host") or "127.0.0.1"
    port = int(daemon_cfg.get("port") or 7090)
    port = _resolve_autostart_daemon_port(
        logger,
        host_cfg,
        daemon_host=host,
        daemon_port=port,
    )
    allow_tools = daemon_cfg.get("allowed_tools") or daemon_cfg.get("allow_tools")
    if isinstance(allow_tools, str):
        allow_tools = [item.strip() for item in allow_tools.split(",") if item.strip()]
    if not isinstance(allow_tools, list):
        allow_tools = None

    log_path = daemon_cfg.get("log_file")
    if log_path:
        log_path = Path(os.path.expanduser(str(log_path)))
    else:
        log_path = log_dir / "aeiva-host.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "aeiva.host.host_cli", "--host", host, "--port", str(port)]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    if allow_tools:
        cmd.extend(["--allow", ",".join(allow_tools)])

    try:
        log_handle = open(log_path, "a", encoding="utf-8")
        process = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=startup_env,
        )
        logger.info("Host daemon started (pid=%s, log=%s).", process.pid, log_path)
        return process
    except Exception as exc:
        logger.warning("Failed to start host daemon: %s", exc)
        return None


def _try_stop_host(logger, host_process):
    if host_process is None:
        return
    try:
        if host_process.poll() is None:
            host_process.terminate()
            host_process.wait(timeout=10)
            logger.info("Host daemon stopped.")
        else:
            logger.warning("Host daemon already stopped.")
    except subprocess.TimeoutExpired:
        logger.warning("Host daemon did not terminate in time; killing.")
        try:
            host_process.kill()
            host_process.wait(timeout=5)
        except Exception as exc:
            logger.warning("Failed to kill host daemon: %s", exc)
    except Exception as exc:
        logger.warning("Host daemon stop failed: %s", exc)


@click.command(name="aeiva-gateway")
@click.option("--config", "-c", default=str(DEFAULT_CONFIG_PATH),
              help="Path to the configuration file (YAML or JSON).",
              type=click.Path(exists=True, dir_okay=False))
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
def run(config, verbose):
    logger = setup_command_logger(
        log_filename="aeiva-gateway.log",
        verbose=verbose,
    )

    click.echo(f"Loading configuration from {config}")
    config_path = Path(config)
    config_dict = from_json_or_yaml(config_path)
    prepare_runtime_config(config_dict)

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

    host_process = _try_start_host(logger, config_dict, LOGS_DIR, config_path)

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
        _try_stop_host(logger, host_process)
        logger.info("Gateway shutdown complete.")


if __name__ == "__main__":
    run()
