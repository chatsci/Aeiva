from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from aeiva.event.event_names import EventNames

from .orchestrator import get_metaui_orchestrator


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetaUIEventBridgeConfig:
    enabled: bool = True
    poll_timeout_seconds: float = 1.0
    emit_timeout_seconds: float = 5.0
    change_event_min_interval_seconds: float = 0.35
    # Empty means pass through all UI event types (recommended).
    allowed_event_types: tuple[str, ...] = ()


def build_metaui_event_prompt(event: Mapping[str, Any]) -> str:
    """
    Build a deterministic LLM-facing description for a UI event.

    This keeps MetaUI passive: the bridge only forwards structured interaction
    data to AI; all UI decisions remain on the AI side.
    """
    event_view = {
        "ui_id": event.get("ui_id"),
        "session_id": event.get("session_id"),
        "component_id": event.get("component_id"),
        "event_type": event.get("event_type"),
        "payload": event.get("payload") if isinstance(event.get("payload"), Mapping) else {},
        "metadata": event.get("metadata") if isinstance(event.get("metadata"), Mapping) else {},
        "ts": event.get("ts"),
    }
    payload_json = json.dumps(event_view, ensure_ascii=False, sort_keys=True)
    return (
        "MetaUI interaction event received.\n"
        "Treat this as the user's latest structured UI input.\n"
        f"event={payload_json}\n"
        "Do not respond with text-only confirmation.\n"
        "Decide next step on AI side and apply it via "
        "metaui(operation='set_state', ...)/metaui(operation='patch', ...) "
        "or metaui(operation='render_full', spec=...) when structure must change."
    )


class MetaUIEventBridge:
    """
    Poll MetaUI events and forward them into the normal perception pipeline.

    This matches A2UI-style flow where UI interactions become model-visible
    events that the agent can reason over in subsequent tool calls.
    """

    def __init__(
        self,
        *,
        queue_gateway: Any,
        agent_loop_getter: Callable[[], Optional[asyncio.AbstractEventLoop]],
        route_token: Optional[str],
        config: MetaUIEventBridgeConfig,
    ) -> None:
        self._queue_gateway = queue_gateway
        self._agent_loop_getter = agent_loop_getter
        self._route_token = route_token
        self._config = config

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._recent_change_events: Dict[str, float] = {}
        self._recent_change_lock = threading.Lock()

    def start(self) -> bool:
        if not self._config.enabled:
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_thread,
            name="metaui-event-bridge",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(0.1, float(timeout)))

    def _run_thread(self) -> None:
        try:
            asyncio.run(self._run_loop())
        except Exception:  # pragma: no cover - defensive thread boundary
            logger.exception("MetaUI event bridge crashed.")

    async def _run_loop(self) -> None:
        orchestrator = get_metaui_orchestrator()
        try:
            await orchestrator.ensure_started()
        except Exception as exc:
            logger.warning("MetaUI event bridge disabled (orchestrator unavailable): %s", exc)
            return

        timeout = max(0.1, float(self._config.poll_timeout_seconds))
        requested_event_types = (
            list(self._config.allowed_event_types)
            if self._config.allowed_event_types
            else None
        )
        while not self._stop_event.is_set():
            try:
                result = await orchestrator.wait_event(
                    timeout=timeout,
                    consume=True,
                    event_types=requested_event_types,
                )
            except Exception as exc:
                logger.debug("MetaUI event bridge wait_event failed: %s", exc)
                await asyncio.sleep(min(1.0, timeout))
                continue

            if not result.get("success"):
                if result.get("error") == "timeout":
                    continue
                logger.debug("MetaUI event bridge wait_event result: %s", result.get("error"))
                continue

            event = result.get("event")
            if not isinstance(event, Mapping):
                continue
            if self._should_skip_event(event):
                continue
            self._emit_to_agent(event)

    def _should_skip_event(self, event: Mapping[str, Any]) -> bool:
        event_type = str(event.get("event_type") or "").strip().lower()
        if event_type != "change":
            return False

        component_id = str(event.get("component_id") or "")
        ui_id = str(event.get("ui_id") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        payload_sig = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        key = f"{ui_id}:{component_id}:{event_type}:{payload_sig}"

        now = time.monotonic()
        with self._recent_change_lock:
            ttl = max(0.0, float(self._config.change_event_min_interval_seconds))
            previous = self._recent_change_events.get(key)
            if previous is not None and (now - previous) < ttl:
                return True
            self._recent_change_events[key] = now

            stale_before = now - max(5.0, ttl * 4.0)
            stale_keys = [item for item, ts in self._recent_change_events.items() if ts < stale_before]
            for stale_key in stale_keys:
                self._recent_change_events.pop(stale_key, None)
        return False

    def _emit_to_agent(self, event: Mapping[str, Any]) -> None:
        loop = self._agent_loop_getter()
        if loop is None:
            logger.debug("MetaUI event dropped: agent event loop not ready.")
            return

        prompt = build_metaui_event_prompt(event)
        meta = {
            "metaui_event": dict(event),
            "metaui_bridge": True,
            "metaui_ui_id": event.get("ui_id"),
            "metaui_session_id": event.get("session_id"),
        }
        signal = self._queue_gateway.build_input_signal(
            prompt,
            source=EventNames.PERCEPTION_GRADIO,
            route=self._route_token,
            meta=meta,
        )
        future = asyncio.run_coroutine_threadsafe(
            self._queue_gateway.emit_input(
                signal,
                route=self._route_token,
                add_pending_route=bool(self._route_token),
                event_name=EventNames.PERCEPTION_STIMULI,
            ),
            loop,
        )
        try:
            future.result(timeout=max(0.2, float(self._config.emit_timeout_seconds)))
        except Exception as exc:
            logger.debug("MetaUI event bridge emit failed: %s", exc)


def parse_metaui_event_bridge_config(config_dict: Mapping[str, Any]) -> MetaUIEventBridgeConfig:
    metaui_cfg = config_dict.get("metaui_config") if isinstance(config_dict, Mapping) else None
    if not isinstance(metaui_cfg, Mapping):
        return MetaUIEventBridgeConfig(enabled=False)

    def _as_float(value: Any, default: float, minimum: float) -> float:
        try:
            parsed = float(value)
        except Exception:
            return default
        if parsed < minimum:
            return default
        return parsed

    enabled = bool(metaui_cfg.get("enabled", False)) and bool(
        metaui_cfg.get("event_bridge_enabled", True)
    )
    poll_timeout = _as_float(metaui_cfg.get("event_bridge_poll_timeout_seconds"), 1.0, 0.1)
    emit_timeout = _as_float(metaui_cfg.get("event_bridge_emit_timeout_seconds"), 5.0, 0.2)
    change_interval = _as_float(metaui_cfg.get("event_bridge_change_throttle_seconds"), 0.35, 0.0)

    raw_types = metaui_cfg.get("event_bridge_event_types")
    event_types: list[str] = []
    if isinstance(raw_types, Sequence) and not isinstance(raw_types, (str, bytes)):
        for item in raw_types:
            token = str(item or "").strip().lower()
            if token:
                event_types.append(token)

    return MetaUIEventBridgeConfig(
        enabled=enabled,
        poll_timeout_seconds=poll_timeout,
        emit_timeout_seconds=emit_timeout,
        change_event_min_interval_seconds=change_interval,
        allowed_event_types=tuple(dict.fromkeys(event_types)),
    )


def start_metaui_event_bridge(
    *,
    config_dict: Mapping[str, Any],
    queue_gateway: Any,
    agent_loop_getter: Callable[[], Optional[asyncio.AbstractEventLoop]],
    route_token: Optional[str],
) -> Optional[MetaUIEventBridge]:
    config = parse_metaui_event_bridge_config(config_dict)
    if not config.enabled:
        return None
    bridge = MetaUIEventBridge(
        queue_gateway=queue_gateway,
        agent_loop_getter=agent_loop_getter,
        route_token=route_token,
        config=config,
    )
    bridge.start()
    return bridge
