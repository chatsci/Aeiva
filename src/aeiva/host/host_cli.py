import json
from pathlib import Path
from typing import Any, Dict, Optional

import click

from aeiva.command.command_utils import get_package_root, resolve_env_vars
from aeiva.host.host_daemon import build_app
from aeiva.host.command_policy import ShellCommandPolicy


DEFAULT_CONFIG_PATH = get_package_root() / "configs" / "host_config.yaml"


def _load_config(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    if path.suffix.lower() in {".yaml", ".yml"}:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_daemon_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    if "host_daemon" in cfg:
        return cfg.get("host_daemon") or {}
    if "host_config" in cfg:
        return cfg.get("host_config") or {}
    return cfg


def _resolve_bind_settings(daemon_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve bind host/port and allowlist from config, supporting nested daemon blocks."""
    host = daemon_cfg.get("host")
    port = daemon_cfg.get("port")
    allowed_tools = daemon_cfg.get("allowed_tools")
    auth_token = daemon_cfg.get("auth_token")
    auth_token_env_var = daemon_cfg.get("auth_token_env_var")
    require_auth = daemon_cfg.get("require_auth")

    nested = daemon_cfg.get("daemon")
    if isinstance(nested, dict):
        host = host or nested.get("host")
        port = port or nested.get("port")
        allowed_tools = allowed_tools or nested.get("allowed_tools")
        auth_token = auth_token or nested.get("auth_token")
        auth_token_env_var = auth_token_env_var or nested.get("auth_token_env_var")
        if require_auth is None:
            require_auth = nested.get("require_auth")

    return {
        "host": host,
        "port": port,
        "allowed_tools": allowed_tools,
        "auth_token": auth_token,
        "auth_token_env_var": auth_token_env_var,
        "require_auth": True if require_auth is None else bool(require_auth),
    }


@click.command()
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to host config (defaults to configs/host_config.yaml if present).",
)
@click.option("--host", "bind_host", default=None, help="Bind host override.")
@click.option("--port", "bind_port", default=None, type=int, help="Bind port override.")
@click.option("--allow", "allow_list", default=None, help="Comma-separated allowed tools.")
@click.option("--no-auth", is_flag=True, help="Disable bearer auth (not recommended).")
def run(
    config_path: Optional[str],
    bind_host: Optional[str],
    bind_port: Optional[int],
    allow_list: Optional[str],
    no_auth: bool,
):
    cfg_path = Path(config_path) if config_path else (DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None)
    cfg = resolve_env_vars(_load_config(cfg_path))
    daemon_cfg = _extract_daemon_cfg(cfg)
    bind_cfg = _resolve_bind_settings(daemon_cfg)

    host = bind_host or bind_cfg.get("host") or "0.0.0.0"
    port = bind_port or bind_cfg.get("port") or 7090

    allowed = None
    raw_allowed = allow_list or bind_cfg.get("allowed_tools")
    if isinstance(raw_allowed, str):
        allowed = [item.strip() for item in raw_allowed.split(",") if item.strip()]
    elif isinstance(raw_allowed, list):
        allowed = [str(item) for item in raw_allowed]

    auth_token = bind_cfg.get("auth_token")
    auth_token_env_var = bind_cfg.get("auth_token_env_var")
    require_auth = bool(bind_cfg.get("require_auth", True))
    if no_auth:
        require_auth = False

    command_policy = ShellCommandPolicy.from_dict(daemon_cfg.get("exec_policy"))
    try:
        app = build_app(
            allowed_tools=allowed,
            command_policy=command_policy,
            auth_token=auth_token,
            auth_token_env_var=auth_token_env_var,
            require_auth=require_auth,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
