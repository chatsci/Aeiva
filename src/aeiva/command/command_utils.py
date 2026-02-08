"""
Here we put util functions related to database, logging and so on for different aeiva commands execution.
"""

import os
from pathlib import Path
import importlib.resources as importlib_resources
from typing import Any, Dict
from aeiva.common.logger import setup_logging
from aeiva.command.config_validation import validate_runtime_config

_DEFAULT_SECRET_ENV_VARS: Dict[str, str] = {
    "llm_api_key": "OPENAI_API_KEY",
    "api_key": "OPENAI_API_KEY",
    "bot_token": "SLACK_BOT_TOKEN",
    "app_token": "SLACK_APP_TOKEN",
}


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


def setup_command_logger(
    *,
    log_filename: str,
    verbose: bool,
    project_root: Path = None,
):
    """
    Build a command logger with a writable fallback path.

    Log preference order:
    1) ~/.aeiva/logs/<log_filename>
    2) <project_root>/logs/<log_filename> when home log dir is not writable
    """
    if project_root is None:
        project_root = get_package_root()

    logger_config_path = project_root / "configs" / "logger_config.yaml"
    log_dir = get_log_dir()
    log_file_path = log_dir / log_filename
    if not os.access(log_dir, os.W_OK):
        fallback_dir = project_root / "logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = fallback_dir / log_filename
    return setup_logging(
        config_file_path=logger_config_path,
        log_file_path=log_file_path,
        verbose=verbose,
    )


def resolve_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve *_env_var keys in a config dict by pulling from os.environ.

    Example:
        {"llm_api_key_env_var": "OPENAI_API_KEY"} -> {"llm_api_key": "..."}
    """
    def _normalize_secret_value(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

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
            current_value = _normalize_secret_value(mapping.get(target_key))
            if current_value:
                mapping[target_key] = current_value
                continue
            env_value = _normalize_secret_value(os.getenv(value))
            if env_value:
                mapping[target_key] = env_value

        for key, env_name in _DEFAULT_SECRET_ENV_VARS.items():
            current_value = _normalize_secret_value(mapping.get(key))
            if current_value:
                mapping[key] = current_value
                continue
            env_value = _normalize_secret_value(os.getenv(env_name))
            if env_value:
                mapping[key] = env_value

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


def prepare_runtime_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve env vars, normalize config shape, and validate runtime config.

    The operation mutates and returns `config_dict` for efficient command startup.
    """
    resolve_env_vars(config_dict)
    try:
        from aeiva.metaui import configure_metaui_runtime
        configure_metaui_runtime(config_dict)
    except Exception:
        # MetaUI is optional at runtime; config wiring must not break startup.
        pass
    validate_runtime_config(config_dict)
    return config_dict


def build_runtime(config_dict: Dict[str, Any]):
    """
    Build either a single Agent or a MultiAgentSystem based on config.

    Returns:
        (runtime, main_agent)
    """
    from aeiva.agent.agent import Agent
    prepare_runtime_config(config_dict)
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
    prepare_runtime_config(config_dict)
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
