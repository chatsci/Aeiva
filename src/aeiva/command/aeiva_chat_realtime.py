"""
Aeiva Multimodal Real-Time Chat command.

Uses FastRTC for WebRTC streaming (mic/speaker via STT/TTS) combined with
a Gradio UI for text input, chatbot display, and file uploads.

Launch:
    aeiva-chat-realtime --config configs/agent_config_realtime.yaml

Requires the 'realtime' extra:
    pip install -e ".[realtime]"
"""

import os
import sys
import threading
import asyncio
import queue
import logging
from typing import Any, Optional

import click
from dotenv import load_dotenv

from aeiva.util.file_utils import from_json_or_yaml
from aeiva.util.path_utils import get_project_root_dir
from aeiva.common.logger import setup_logging
from aeiva.command.command_utils import get_package_root, get_log_dir, build_runtime
from aeiva.command.gateway_registry import GatewayRegistry
from aeiva.interface.gateway_base import ResponseQueueGateway

logger = logging.getLogger(__name__)

PACKAGE_ROOT = get_package_root()
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / 'configs' / 'agent_config_realtime.yaml'

LOGS_DIR = get_log_dir()
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_PATH = LOGS_DIR / 'aeiva-chat-realtime.log'


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
        from fastrtc import ReplyOnPause, WebRTC
        return gr, ReplyOnPause, WebRTC
    except ImportError as e:
        click.echo(
            "Error: FastRTC is not installed. "
            "Install it with: pip install -e '.[realtime]'\n"
            f"Details: {e}"
        )
        sys.exit(1)


@click.command(name="aeiva-chat-realtime")
@click.option('--config', '-c', default=str(DEFAULT_CONFIG_PATH),
              help='Path to the configuration file (YAML or JSON).',
              type=click.Path(exists=True, dir_okay=False))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging.')
def run(config, verbose):
    """Starts the Aeiva multimodal real-time chat interface."""

    # 1. Setup logging
    project_root = get_project_root_dir()
    logger_config_path = project_root / "configs" / "logger_config.yaml"
    log = setup_logging(
        config_file_path=logger_config_path,
        log_file_path=DEFAULT_LOG_PATH,
        verbose=verbose,
    )

    # 2. Load environment variables
    load_dotenv()

    log.info(f"Loading configuration from {config}")
    config_dict = from_json_or_yaml(config)

    realtime_cfg = config_dict.get("realtime_config", {})
    realtime_mode = realtime_cfg.get("mode", "turn_based")
    realtime_provider = realtime_cfg.get("provider", "openai")

    if realtime_mode == "live":
        run_live_realtime_ui(config_dict, log, realtime_provider)
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

    # 6. Optionally start Neo4j (skip if NEO4J_HOME not set)
    neo4j_home = os.getenv('NEO4J_HOME')
    neo4j_process = None
    if neo4j_home:
        try:
            from aeiva.command.command_utils import validate_neo4j_home, start_neo4j
            validate_neo4j_home(log, neo4j_home)
            neo4j_process = start_neo4j(log, neo4j_home)
        except SystemExit:
            log.warning("Neo4j validation failed, continuing without Neo4j.")
            neo4j_process = None
    else:
        log.info("NEO4J_HOME not set. Skipping Neo4j startup (optional for realtime mode).")

    demo, _handler = build_turn_based_realtime_ui(
        config_dict=config_dict,
        agent=agent,
        queue_gateway=queue_gateway,
        response_queue=response_queue,
        log=log,
    )

    log.info("Launching Gradio interface...")
    demo.launch(share=True)

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

    if neo4j_process:
        from aeiva.command.command_utils import stop_neo4j
        stop_neo4j(log, neo4j_process)


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

    from aeiva.command.stt_tts_factory import create_stt_model, create_tts_model

    realtime_cfg = config_dict.get("realtime_config", {})
    log.info("Loading STT model (backend=%s)...", realtime_cfg.get("stt", {}).get("backend", "fastrtc"))
    stt_model = create_stt_model(realtime_cfg)
    log.info("Loading TTS model (backend=%s)...", realtime_cfg.get("tts", {}).get("backend", "fastrtc"))
    tts_model = create_tts_model(realtime_cfg)
    log.info("STT/TTS models loaded.")

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

    class SafeReplyOnPause(ReplyOnPause):
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

    with gr.Blocks(title="AEIVA Multimodal Real-Time Chat") as demo:
        gr.HTML(
            "<h1 style='text-align:center;'>AEIVA - Multimodal Real-Time Chat</h1>"
            "<p style='text-align:center;'>Speak, type, or enable the camera for multimodal chat.</p>"
        )

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

                webrtc = WebRTC(
                    modality="audio",
                    mode="send-receive",
                    variant="textbox",
                )

                webrtc_time_limit = int(realtime_cfg.get("webrtc_time_limit", 90))
                webrtc.stream(
                    SafeReplyOnPause(handler, can_interrupt=False),
                    inputs=[webrtc, chatbot, camera_input, upload_image],
                    outputs=[webrtc],
                    time_limit=webrtc_time_limit,
                    send_input_on="submit",
                )
                webrtc.on_additional_outputs(
                    lambda old, new: new,
                    inputs=[chatbot],
                    outputs=[chatbot],
                )

                with gr.Row():
                    clear_btn = gr.Button("Clear History")
                    clear_btn.click(lambda: [], outputs=[chatbot])

    return demo, handler


def run_live_realtime_ui(config_dict: dict, log: logging.Logger, provider: str) -> None:
    """Launch live (true realtime) audio+video mode using provider APIs."""
    try:
        import gradio as gr
        from gradio_webrtc import WebRTC
    except ImportError as e:
        click.echo(
            "Error: gradio-webrtc is required for live realtime mode. "
            "Install with: pip install -e '.[realtime]'\n"
            f"Details: {e}"
        )
        sys.exit(1)

    if provider != "openai":
        click.echo(f"Provider '{provider}' is not implemented yet. Use provider: openai.")
        sys.exit(1)

    from aeiva.realtime.openai_realtime import OpenAIRealtimeConfig, OpenAIRealtimeHandler

    llm_cfg = config_dict.get("llm_gateway_config", {})
    api_key = llm_cfg.get("llm_api_key")
    if not api_key:
        env_var = llm_cfg.get("llm_api_key_env_var")
        if env_var:
            api_key = os.getenv(env_var)
    if not api_key:
        click.echo("Error: OpenAI API key is required for live realtime mode.")
        sys.exit(1)

    cfg = config_dict.get("realtime_config", {})
    openai_cfg = cfg.get("openai", {})
    live_config = OpenAIRealtimeConfig(
        api_key=api_key,
        model=openai_cfg.get("model", "gpt-realtime"),
        base_url=openai_cfg.get("base_url", "wss://api.openai.com/v1/realtime"),
        instructions=openai_cfg.get("instructions"),
        voice=openai_cfg.get("voice", "alloy"),
        input_audio_format=openai_cfg.get("input_audio_format", "pcm16"),
        output_audio_format=openai_cfg.get("output_audio_format", "pcm16"),
        turn_detection=openai_cfg.get("turn_detection", True),
        send_video=openai_cfg.get("send_video", False),
        video_fps=openai_cfg.get("video_fps", 1.0),
    )

    handler = OpenAIRealtimeHandler(live_config)

    with gr.Blocks(title="AEIVA Multimodal Real-Time Chat") as demo:
        gr.HTML(
            "<h1 style='text-align:center;'>AEIVA - Multimodal Real-Time Chat</h1>"
            "<p style='text-align:center;'>Live audio+video streaming (OpenAI realtime).</p>"
        )

        with gr.Row():
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### Settings")
                gr.Markdown(f"**Mode:** `live`")
                gr.Markdown(f"**Provider:** `{provider}`")
                gr.Markdown(f"**Model:** `{live_config.model}`")
                gr.Markdown("### Notes")
                gr.Markdown(
                    "*Live mode streams audio continuously. Video frames can be sent "
                    "if enabled in realtime_config.openai.send_video.*"
                )

            with gr.Column(scale=2, min_width=500):
                chatbot = gr.Chatbot(type="messages", height=600)

                webrtc = WebRTC(
                    modality="audio-video",
                    mode="send-receive",
                )

                webrtc_time_limit = int(cfg.get("webrtc_time_limit", 90))
                webrtc.stream(
                    handler,
                    inputs=[webrtc, chatbot],
                    outputs=[webrtc],
                    time_limit=webrtc_time_limit,
                )
                webrtc.on_additional_outputs(
                    lambda old, new: new,
                    inputs=[chatbot],
                    outputs=[chatbot],
                )

                with gr.Row():
                    txt = gr.Textbox(
                        show_label=False,
                        placeholder="Type a message and press Enter (sent to the live session)",
                        lines=1,
                        scale=4,
                    )

                async def text_submit(user_text, history):
                    if not user_text or not user_text.strip():
                        return history, ""
                    history = list(history) if history else []
                    history.append({"role": "user", "content": user_text})
                    handler_instance = OpenAIRealtimeHandler.get_active() or handler
                    handler_instance.chatbot = list(history)
                    try:
                        await handler_instance.send_text(user_text)
                    except Exception as e:
                        log.error(f"Failed to send live text: {e}")
                        history.append({"role": "assistant", "content": f"Error: {e}"})
                    return history, ""

                txt.submit(
                    text_submit,
                    inputs=[txt, chatbot],
                    outputs=[chatbot, txt],
                )

                clear_btn = gr.Button("Clear History")
                clear_btn.click(lambda: ([], ""), outputs=[chatbot, txt])

        log.info("Launching live realtime Gradio interface...")
        demo.launch(share=True)
