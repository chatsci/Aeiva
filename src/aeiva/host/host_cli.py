import json
from pathlib import Path
from typing import Any, Dict, Optional

import click

from aeiva.command.command_utils import get_package_root, resolve_env_vars
from aeiva.host.host_daemon import build_app


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
def run(config_path: Optional[str], bind_host: Optional[str], bind_port: Optional[int], allow_list: Optional[str]):
    cfg_path = Path(config_path) if config_path else (DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None)
    cfg = resolve_env_vars(_load_config(cfg_path))
    daemon_cfg = _extract_daemon_cfg(cfg)

    host = bind_host or daemon_cfg.get("host") or "0.0.0.0"
    port = bind_port or daemon_cfg.get("port") or 7090

    allowed = None
    raw_allowed = allow_list or daemon_cfg.get("allowed_tools")
    if isinstance(raw_allowed, str):
        allowed = [item.strip() for item in raw_allowed.split(",") if item.strip()]
    elif isinstance(raw_allowed, list):
        allowed = [str(item) for item in raw_allowed]

    app = build_app(allowed_tools=allowed)

    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
