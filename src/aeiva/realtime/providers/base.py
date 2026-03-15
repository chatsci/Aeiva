from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict


class LiveRealtimeProvider(ABC):
    """
    Base contract for live realtime (full-duplex) providers.

    Providers own transport details and UI wiring so gateway orchestration stays
    provider-agnostic.
    """

    provider_name: str = "unknown"

    def __init__(self, config_dict: Dict[str, Any], logger: logging.Logger) -> None:
        self.config_dict = config_dict
        self.logger = logger
        self.realtime_cfg = (
            config_dict.get("realtime_config")
            if isinstance(config_dict, dict)
            else {}
        ) or {}

    def _build_gradio_launch_kwargs(self, *, prevent_thread_lock: bool = False) -> Dict[str, Any]:
        launch_kwargs: Dict[str, Any] = {
            "share": bool(self.realtime_cfg.get("share", True)),
        }
        server_name = self.realtime_cfg.get("server_name")
        if server_name:
            launch_kwargs["server_name"] = str(server_name)
        server_port = self.realtime_cfg.get("server_port")
        if server_port is not None and str(server_port).strip() != "":
            launch_kwargs["server_port"] = int(server_port)
        if prevent_thread_lock:
            launch_kwargs["prevent_thread_lock"] = True
        return launch_kwargs

    def _launch_demo_with_recovery(self, demo: Any, launch_kwargs: Dict[str, Any]) -> None:
        """
        Launch gradio demo with optional port-conflict fallback.

        When a fixed `server_port` is configured and already occupied, Gradio
        raises OSError. We can optionally retry without fixed port so startup
        succeeds instead of crashing.
        """
        try:
            demo.launch(**launch_kwargs)
            return
        except OSError as exc:
            configured_port = launch_kwargs.get("server_port")
            fallback_enabled = bool(
                self.realtime_cfg.get("server_port_auto_fallback_on_conflict", True)
            )
            conflict_msg = "Cannot find empty port in range"
            if not (
                fallback_enabled
                and configured_port is not None
                and conflict_msg in str(exc)
            ):
                raise

            retry_kwargs = dict(launch_kwargs)
            retry_kwargs.pop("server_port", None)
            self.logger.warning(
                "Configured realtime UI port %s is occupied; retrying with auto-selected free port.",
                configured_port,
            )
            demo.launch(**retry_kwargs)

    @abstractmethod
    def launch(self, *, prevent_thread_lock: bool = False) -> None:
        """
        Build and launch the provider-specific realtime UI.
        """
        raise NotImplementedError
