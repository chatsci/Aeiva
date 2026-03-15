"""
Aeiva Multimodal Real-Time Chat command.

Uses FastRTC for WebRTC streaming (mic/speaker via STT/TTS) combined with
a Gradio UI for text input, chatbot display, and file uploads.

Launch:
    aeiva-chat-realtime --config configs/agent_config_realtime.yaml

Requires the 'realtime' extra:
    pip install -e ".[realtime]"
"""

import sys
import os
import signal
import threading
import asyncio
import queue
import logging
import socket
import subprocess
import time
from contextlib import nullcontext
from typing import Any, Optional

import click
from dotenv import load_dotenv

from aeiva.util.file_utils import from_json_or_yaml
from aeiva.command.command_utils import (
    get_package_root,
    build_runtime,
    prepare_runtime_config,
    setup_command_logger,
)
from aeiva.command.gateway_registry import GatewayRegistry
from aeiva.interface.gateway_base import ResponseQueueGateway

logger = logging.getLogger(__name__)

PACKAGE_ROOT = get_package_root()
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / 'configs' / 'agent_config_realtime.yaml'


def _build_safe_reply_on_pause_class(reply_on_pause_cls):
    """
    Wrap a ReplyOnPause-compatible class with emit re-entrancy protection.

    FastRTC clones stream handlers via `.copy()` for each connection. The upstream
    `ReplyOnPause.copy()` returns the base class, which drops subclass safeguards.
    We override `copy()` here so every cloned handler keeps the lock-guarded
    `emit()` implementation.
    """

    class SafeReplyOnPause(reply_on_pause_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._emit_lock = threading.Lock()

        def emit(self):
            if not self._emit_lock.acquire(blocking=False):
                return None
            try:
                return super().emit()
            finally:
                self._emit_lock.release()

        def copy(self):
            return self.__class__(
                self.fn,
                self.startup_fn,
                self.algo_options,
                self.model_options,
                self.can_interrupt,
                self.expected_layout,
                self.output_sample_rate,
                self.output_frame_size,
                self.input_sample_rate,
                self.model,
                self.needs_args,
            )

    return SafeReplyOnPause


def _try_import_fastrtc():
    """Import core FastRTC UI components, raising a clear error if not installed.

    STT/TTS model loading is handled separately by
    :func:`aeiva.command.stt_tts_factory.create_stt_model` /
    :func:`aeiva.command.stt_tts_factory.create_tts_model`.
    """
    try:
        import gradio as gr
        try:
            import gradio.routes as gr_routes
            gr_routes.print = lambda *args, **kwargs: None
        except ImportError:
            pass
        from fastrtc import ReplyOnPause, WebRTC as FastRTCWebRTC
        from aeiva.realtime.fastrtc_webrtc import build_safe_webrtc_component

        WebRTC = build_safe_webrtc_component(FastRTCWebRTC)
        return gr, ReplyOnPause, WebRTC
    except ImportError as e:
        click.echo(
            "Error: FastRTC is not installed. "
            "Install it with: pip install -e '.[realtime]'\n"
            f"Details: {e}"
        )
        sys.exit(1)


def _build_turn_based_launch_kwargs(
    realtime_cfg: dict | None,
    *,
    prevent_thread_lock: bool = False,
) -> dict:
    cfg = realtime_cfg or {}
    kwargs = {
        "share": bool(cfg.get("share", True)),
    }
    server_name = cfg.get("server_name")
    if server_name:
        kwargs["server_name"] = str(server_name)
    server_port = cfg.get("server_port")
    if server_port is not None and str(server_port).strip() != "":
        kwargs["server_port"] = int(server_port)
    if prevent_thread_lock:
        kwargs["prevent_thread_lock"] = True
    return kwargs


def _extract_launch_urls(launch_result: Any) -> tuple[Optional[str], Optional[str]]:
    """Best-effort extraction of local/share URLs from ``gradio.Blocks.launch`` return."""
    local_url: Optional[str] = None
    share_url: Optional[str] = None

    if isinstance(launch_result, tuple):
        if len(launch_result) >= 2 and isinstance(launch_result[1], str):
            local_url = launch_result[1]
        if len(launch_result) >= 3 and isinstance(launch_result[2], str):
            share_url = launch_result[2]
        return local_url, share_url

    local_candidate = getattr(launch_result, "local_url", None)
    share_candidate = getattr(launch_result, "share_url", None)
    if isinstance(local_candidate, str):
        local_url = local_candidate
    if isinstance(share_candidate, str):
        share_url = share_candidate
    return local_url, share_url


def _log_launch_urls(launch_result: Any, log: logging.Logger) -> None:
    local_url, share_url = _extract_launch_urls(launch_result)
    if local_url:
        log.info("Realtime UI URL: %s", local_url)
    if share_url:
        log.info("Realtime UI share URL: %s", share_url)


def _is_local_host(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def _port_is_listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=0.35):
            return True
    except OSError:
        return False


def _list_listening_pids(port: int) -> list[int]:
    try:
        proc = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{int(port)}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            check=False,
            timeout=1.5,
        )
    except Exception:
        return []
    pids: list[int] = []
    for line in (proc.stdout or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            pids.append(int(raw))
        except ValueError:
            continue
    return pids


def _command_for_pid(pid: int) -> str:
    try:
        proc = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
            timeout=1.0,
        )
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def _reclaim_aeiva_port_if_needed(realtime_cfg: dict | None, log: logging.Logger) -> None:
    cfg = realtime_cfg or {}
    reclaim_enabled = bool(cfg.get("server_port_reclaim_aeiva_process", True))
    if not reclaim_enabled:
        return
    server_port = cfg.get("server_port")
    if server_port is None or str(server_port).strip() == "":
        return
    host = str(cfg.get("server_name") or "127.0.0.1")
    if not _is_local_host(host):
        return
    port = int(server_port)
    if not _port_is_listening(host, port):
        return

    aeiva_markers = (
        "aeiva-gateway",
        "aeiva-chat-realtime",
        "aeiva.command.aeiva_gateway",
        "aeiva.command.aeiva_chat_realtime",
    )
    reclaimed_any = False
    non_aeiva_occupiers: list[tuple[int, str]] = []
    for pid in _list_listening_pids(port):
        if pid == os.getpid():
            continue
        cmd = _command_for_pid(pid)
        if not any(marker in cmd for marker in aeiva_markers):
            non_aeiva_occupiers.append((pid, cmd))
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            reclaimed_any = True
            log.warning(
                "Reclaimed stale Aeiva process on port %s (pid=%s).",
                port,
                pid,
            )
        except Exception as exc:
            log.warning(
                "Failed to reclaim stale Aeiva process on port %s (pid=%s): %s",
                port,
                pid,
                exc,
            )
    if non_aeiva_occupiers:
        summary = "; ".join(
            f"pid={pid} cmd={cmd[:120]}" for pid, cmd in non_aeiva_occupiers[:3]
        )
        log.warning(
            "Configured realtime port %s is occupied by non-Aeiva process(es): %s",
            port,
            summary,
        )
    if reclaimed_any:
        # Allow OS a short window to release socket state.
        deadline = time.time() + 1.5
        while time.time() < deadline:
            if not _port_is_listening(host, port):
                break
            time.sleep(0.1)


def launch_turn_based_demo(
    *,
    demo: Any,
    realtime_cfg: dict | None,
    log: logging.Logger,
    prevent_thread_lock: bool = False,
) -> None:
    _reclaim_aeiva_port_if_needed(realtime_cfg, log)
    launch_kwargs = _build_turn_based_launch_kwargs(
        realtime_cfg,
        prevent_thread_lock=prevent_thread_lock,
    )
    try:
        launch_result = demo.launch(**launch_kwargs)
        _log_launch_urls(launch_result, log)
        return
    except OSError as exc:
        configured_port = launch_kwargs.get("server_port")
        fallback_enabled = bool(
            (realtime_cfg or {}).get("server_port_auto_fallback_on_conflict", True)
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
        log.warning(
            "Configured realtime UI port %s is occupied; retrying with auto-selected free port.",
            configured_port,
        )
        launch_result = demo.launch(**retry_kwargs)
        _log_launch_urls(launch_result, log)


@click.command(name="aeiva-chat-realtime")
@click.option('--config', '-c', default=str(DEFAULT_CONFIG_PATH),
              help='Path to the configuration file (YAML or JSON).',
              type=click.Path(exists=True, dir_okay=False))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging.')
def run(config, verbose):
    """Starts the Aeiva multimodal real-time chat interface."""

    # 1. Setup logging
    log = setup_command_logger(
        log_filename="aeiva-chat-realtime.log",
        verbose=verbose,
    )

    # 2. Load environment variables
    load_dotenv()

    log.info(f"Loading configuration from {config}")
    config_dict = from_json_or_yaml(config)
    prepare_runtime_config(config_dict)

    realtime_cfg = config_dict.get("realtime_config", {})
    realtime_mode = realtime_cfg.get("mode", "turn_based")
    realtime_provider = realtime_cfg.get("provider", "openai")
    from aeiva.liferpg.panel import (
        is_liferpg_separate_page_enabled,
        launch_liferpg_standalone_app,
    )

    if realtime_mode == "live":
        if is_liferpg_separate_page_enabled(config_dict):
            log.info("Launching LifeRPG standalone UI...")
            launch_liferpg_standalone_app(
                config_dict=config_dict,
                prevent_thread_lock=True,
            )
        launch_live_realtime_ui(
            config_dict=config_dict,
            log=log,
            provider=realtime_provider,
            prevent_thread_lock=False,
        )
        return

    # 3. Initialize Agent or MAS (turn-based realtime)
    try:
        runtime, agent = build_runtime(config_dict)
        log.info("Agent initialized successfully.")
    except Exception as e:
        log.error(f"Failed to initialize Agent: {e}")
        click.echo(f"Error: Failed to initialize Agent: {e}")
        sys.exit(1)

    # 4. Start Agent in daemon thread
    raw_memory_cfg = config_dict.get("raw_memory_config", {})
    raw_memory_session = None
    if raw_memory_cfg.get("enabled", True):
        raw_memory_session = {
            "user_id": raw_memory_cfg.get("user_id", "user"),
        }

    def run_agent(runtime_instance):
        try:
            asyncio.run(runtime_instance.run(raw_memory_session=raw_memory_session))
        except Exception as e:
            log.error(f"Error running Agent: {e}")

    agent_thread = threading.Thread(target=run_agent, args=(runtime,), daemon=True)
    agent_thread.start()
    log.info("Agent run thread started.")

    # 5. Create response_queue and register handler
    response_queue = queue.Queue()
    response_timeout = float((config_dict.get("llm_gateway_config") or {}).get("llm_timeout", 60.0))
    registry = GatewayRegistry(config_dict)
    realtime_gateway_cfg = registry.resolve_channel_config("realtime")
    queue_gateway = ResponseQueueGateway(
        realtime_gateway_cfg,
        agent.event_bus,
        response_queue,
        response_timeout=response_timeout,
    )
    queue_gateway.register_handlers()
    log.info("Registered response queue gateway handlers.")

    demo, _handler = build_turn_based_realtime_ui(
        config_dict=config_dict,
        agent=agent,
        queue_gateway=queue_gateway,
        response_queue=response_queue,
        log=log,
    )

    if is_liferpg_separate_page_enabled(config_dict):
        log.info("Launching LifeRPG standalone UI...")
        launch_liferpg_standalone_app(
            config_dict=config_dict,
            prevent_thread_lock=True,
        )

    log.info("Launching Gradio interface...")
    launch_turn_based_demo(
        demo=demo,
        realtime_cfg=realtime_cfg,
        log=log,
        prevent_thread_lock=False,
    )

    # Graceful shutdown: signal the agent to stop and wait for proper cleanup.
    # This allows the agent's finally block to run, which:
    # 1. Emits raw_memory.session.end → raw_memory writes file + emits session.closed
    # 2. SummaryMemoryNeuron processes session.closed → LLM summary + user memory
    log.info("Gradio exited. Requesting agent shutdown...")
    agent.request_stop()
    agent_thread.join(timeout=60)

    if agent_thread.is_alive():
        log.warning("Agent thread did not stop in time. Forcing session close.")
        if agent.raw_memory:
            try:
                agent.raw_memory._close_all_sessions()
            except Exception as e:
                log.error(f"Error in fallback session close: {e}")

    log.info("Agent shutdown complete.")


def build_turn_based_realtime_ui(
    *,
    config_dict: dict,
    agent: Any,
    queue_gateway: ResponseQueueGateway,
    response_queue: queue.Queue,
    log: logging.Logger,
    route_token: Optional[str] = None,
):
    gr, ReplyOnPause, WebRTC = _try_import_fastrtc()
    from aeiva.liferpg.panel import (
        build_liferpg_panel,
        get_liferpg_page_url,
        is_liferpg_separate_page_enabled,
    )

    from aeiva.command.stt_tts_factory import create_stt_model, create_tts_model
    from aeiva.realtime.pause_model import build_pause_detection_model

    realtime_cfg = config_dict.get("realtime_config", {})
    load_mode = str(realtime_cfg.get("model_load_mode", "lazy")).strip().lower() or "lazy"
    log.info(
        "Preparing STT model (backend=%s, load_mode=%s)...",
        realtime_cfg.get("stt", {}).get("backend", "fastrtc"),
        load_mode,
    )
    stt_model = create_stt_model(realtime_cfg)
    log.info(
        "Preparing TTS model (backend=%s, load_mode=%s)...",
        realtime_cfg.get("tts", {}).get("backend", "fastrtc"),
        load_mode,
    )
    tts_model = create_tts_model(realtime_cfg)
    log.info("STT/TTS model handlers ready.")
    pause_model = build_pause_detection_model(realtime_cfg, log=log)
    log.info("Pause detection model ready.")

    from aeiva.command.realtime_handler import RealtimePipelineHandler

    handler = RealtimePipelineHandler(
        agent=agent,
        gateway=queue_gateway,
        response_queue=response_queue,
        stt_model=stt_model,
        tts_model=tts_model,
        config_dict=config_dict,
        route_token=route_token,
    )

    SafeReplyOnPause = _build_safe_reply_on_pause_class(ReplyOnPause)
    liferpg_url = get_liferpg_page_url(config_dict)
    embed_liferpg_panel = not is_liferpg_separate_page_enabled(config_dict)

    with gr.Blocks(
        title="AEIVA Multimodal Real-Time Chat",
        css="""
        .aeiva-link-card {
            margin-top: 14px;
            padding: 14px 16px;
            border-radius: 18px;
            border: 1px solid rgba(25, 74, 66, 0.12);
            background: linear-gradient(180deg, rgba(245, 249, 247, 0.98), rgba(236, 243, 239, 0.98));
        }
        .aeiva-link-card h4 {
            margin: 0;
            font-size: 0.96rem;
        }
        .aeiva-link-card p {
            margin: 8px 0 0;
            color: #52606d;
            line-height: 1.55;
            font-size: 0.92rem;
        }
        .aeiva-link-card a {
            display: inline-flex;
            margin-top: 12px;
            padding: 9px 12px;
            border-radius: 999px;
            background: #143e38;
            color: #f6f3ed;
            text-decoration: none;
            font-size: 0.92rem;
        }
        """,
    ) as demo:
        gr.HTML(
            "<h1 style='text-align:center;'>AEIVA - Multimodal Real-Time Chat</h1>"
            "<p style='text-align:center;'>Speak, type, or enable the camera for multimodal chat.</p>"
        )
        has_tabs = hasattr(gr, "Tabs") and hasattr(gr, "Tab")
        tabs_ctx = gr.Tabs() if has_tabs and embed_liferpg_panel else nullcontext()
        chat_tab_ctx = gr.Tab("Realtime Chat") if has_tabs and embed_liferpg_panel else nullcontext()
        with tabs_ctx:
            with chat_tab_ctx:
                with gr.Row():
                    with gr.Column(scale=1, min_width=300):
                        gr.Markdown("### Settings")
                        gr.Markdown(
                            "**Model:** "
                            f"`{config_dict.get('llm_gateway_config', {}).get('llm_model_name', 'unknown')}`"
                        )
                        gr.Markdown(
                            "**Stream:** "
                            f"`{config_dict.get('llm_gateway_config', {}).get('llm_stream', False)}`"
                        )
                        if liferpg_url:
                            gr.HTML(
                                "<div class='aeiva-link-card'>"
                                "<h4>LifeRPG Dashboard</h4>"
                                "<p>Open the standalone profile and growth panel in a separate page.</p>"
                                f"<a href='{liferpg_url}' target='_blank' rel='noopener'>Open Dashboard</a>"
                                "</div>"
                            )

                        gr.Markdown("### Camera / Image")
                        camera_input = gr.Image(
                            label="Webcam (live)",
                            type="numpy",
                            sources=["webcam"],
                            streaming=True,
                        )
                        upload_image = gr.Image(
                            label="Upload Image",
                            type="numpy",
                            sources=["upload", "clipboard"],
                        )
                        _camera_cache = gr.State(None)
                        camera_input.stream(
                            lambda frame: handler.update_latest_frame(frame),
                            inputs=camera_input,
                            outputs=_camera_cache,
                            show_progress=False,
                        )
                        gr.Markdown(
                            "*Enable webcam to send live frames with your messages. "
                            "The most recent frame is sent when you speak or type.*"
                        )
                        gr.File(label="Upload Files")

                    with gr.Column(scale=2, min_width=500):
                        chatbot = gr.Chatbot(type="messages", height=600)
                        chatbot_seq = gr.State(0)

                        webrtc = WebRTC(
                            modality="audio",
                            mode="send-receive",
                            variant="textbox",
                        )

                        webrtc_time_limit = int(realtime_cfg.get("webrtc_time_limit", 90))
                        webrtc.stream(
                            SafeReplyOnPause(
                                handler,
                                can_interrupt=False,
                                model=pause_model,
                            ),
                            inputs=[webrtc, chatbot, camera_input, upload_image],
                            outputs=[webrtc],
                            time_limit=webrtc_time_limit,
                            send_input_on="submit",
                        )

                        def _normalize_history(history):
                            if not isinstance(history, list):
                                return []
                            normalized = []
                            for item in history:
                                if isinstance(item, dict):
                                    normalized.append(dict(item))
                                else:
                                    normalized.append(item)
                            return normalized

                        def _coerce_seq(value):
                            try:
                                return int(value)
                            except Exception:
                                return 0

                        def _apply_chatbot_update(old_history, old_seq, *additional):
                            prior_history = _normalize_history(old_history)
                            prior_seq = _coerce_seq(old_seq)
                            if len(additional) >= 2:
                                incoming_history = _normalize_history(additional[0])
                                incoming_seq = _coerce_seq(additional[1])
                            elif len(additional) == 1:
                                incoming_history = _normalize_history(additional[0])
                                # Backward-compatible fallback when runtime emits history only.
                                incoming_seq = prior_seq + 1
                            else:
                                return prior_history, prior_seq
                            if incoming_seq <= prior_seq:
                                return prior_history, prior_seq
                            return incoming_history, incoming_seq

                        webrtc.on_additional_outputs(
                            _apply_chatbot_update,
                            inputs=[chatbot, chatbot_seq],
                            outputs=[chatbot, chatbot_seq],
                            queue=False,
                        )

                        with gr.Row():
                            clear_btn = gr.Button("Clear History")
                            clear_btn.click(lambda: ([], 0), outputs=[chatbot, chatbot_seq])

            if has_tabs and embed_liferpg_panel:
                build_liferpg_panel(gr=gr, config_dict=config_dict)

    return demo, handler


def launch_live_realtime_ui(
    *,
    config_dict: dict,
    log: logging.Logger,
    provider: Optional[str] = None,
    prevent_thread_lock: bool = False,
) -> None:
    """Launch live realtime UI using the provider registry."""
    from aeiva.realtime.providers.registry import create_live_realtime_provider

    realtime_cfg = config_dict.get("realtime_config") or {}
    provider_name = str(provider or realtime_cfg.get("provider") or "openai").strip().lower()
    runtime_provider = create_live_realtime_provider(
        config_dict=config_dict,
        logger=log,
        provider_name=provider_name,
    )
    runtime_provider.launch(prevent_thread_lock=prevent_thread_lock)


def run_live_realtime_ui(config_dict: dict, log: logging.Logger, provider: str) -> None:
    """
    Backward-compatible wrapper for external callers.
    """
    launch_live_realtime_ui(
        config_dict=config_dict,
        log=log,
        provider=provider,
        prevent_thread_lock=False,
    )
