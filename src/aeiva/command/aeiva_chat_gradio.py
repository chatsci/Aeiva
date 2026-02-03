"""
Aeiva Chat Gradio command.

Uses ResponseQueueGateway (GatewayBase) for event-driven communication
with the Agent, plus a Gradio UI for text input, chatbot display,
and multimodal file uploads.

Launch:
    aeiva-chat-gradio --config configs/agent_config.yaml

Requires gradio:
    pip install gradio
"""

import os
import sys
import threading
import asyncio
import queue
import logging
from datetime import datetime
from uuid import uuid4
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
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / 'configs' / 'agent_config.yaml'

LOGS_DIR = get_log_dir()
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_PATH = LOGS_DIR / 'aeiva-chat-gradio.log'


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


@click.command(name="aeiva-chat-gradio")
@click.option('--config', '-c', default=str(DEFAULT_CONFIG_PATH),
              help='Path to the configuration file (YAML or JSON).',
              type=click.Path(exists=True, dir_okay=False))
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging.')
def run(config, verbose):
    """
    Starts the Aeiva chat Gradio interface with the provided configuration.
    """
    project_root = get_project_root_dir()
    logger_config_path = project_root / "configs" / "logger_config.yaml"
    log = setup_logging(
        config_file_path=logger_config_path,
        log_file_path=DEFAULT_LOG_PATH,
        verbose=verbose,
    )

    load_dotenv()

    log.info(f"Loading configuration from {config}")
    config_dict = from_json_or_yaml(config)

    # Initialize the Agent
    try:
        runtime, agent = build_runtime(config_dict)
        log.info("Agent initialized successfully.")
    except Exception as e:
        log.error(f"Failed to initialize Agent: {e}")
        click.echo(f"Error: Failed to initialize Agent: {e}")
        sys.exit(1)

    # Start Agent in daemon thread
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

    # Create response queue and gateway
    response_queue = queue.Queue()
    response_timeout = float(
        (config_dict.get("llm_gateway_config") or {}).get("llm_timeout", 60.0)
    )
    registry = GatewayRegistry(config_dict)
    gradio_cfg = registry.resolve_channel_config("gradio")
    queue_gateway = ResponseQueueGateway(
        gradio_cfg,
        agent.event_bus,
        response_queue,
        response_timeout=response_timeout,
    )
    queue_gateway.register_handlers()
    log.info("Registered response queue gateway handlers.")

    # Optionally start Neo4j
    neo4j_process = _try_start_neo4j(log)

    # Build and launch the Gradio UI
    gradio_share = (config_dict.get("gradio_config") or {}).get("share", True)
    demo = build_gradio_chat_ui(
        config_dict=config_dict,
        agent=agent,
        queue_gateway=queue_gateway,
        response_queue=response_queue,
        log=log,
    )

    log.info("Launching Gradio interface...")
    demo.launch(share=gradio_share)

    # Graceful shutdown
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
    _try_stop_neo4j(log, neo4j_process)


def build_gradio_chat_ui(
    *,
    config_dict: dict,
    agent: Any,
    queue_gateway: ResponseQueueGateway,
    response_queue: queue.Queue,
    log: logging.Logger,
    route_token: Optional[str] = None,
):
    """Build and return the Gradio Blocks demo for chat UI.

    This function is also used by the unified gateway (aeiva_gateway.py)
    to embed the Gradio chat interface.
    """
    import gradio as gr
    try:
        import gradio.routes as gr_routes
        gr_routes.print = lambda *args, **kwargs: None
    except Exception:
        pass
    import numpy as np
    import soundfile as sf
    from PIL import Image

    raw_memory_cfg = config_dict.get("raw_memory_config") or {}
    raw_user_id = str(raw_memory_cfg.get("user_id", "user"))

    def _emit_raw_memory(event_name, payload):
        if agent is None or agent.event_bus.loop is None:
            log.warning("Raw memory event skipped (event bus not ready).")
            return False
        emit_future = asyncio.run_coroutine_threadsafe(
            agent.event_bus.emit(event_name, payload=payload),
            agent.event_bus.loop,
        )
        try:
            emit_future.result(timeout=5)
        except Exception as e:
            log.warning(f"Raw memory emit failed: {e}")
            return False
        return True

    def _end_session(session_id):
        if session_id:
            _emit_raw_memory(
                "raw_memory.session.end",
                {"session_id": session_id, "user_id": raw_user_id},
            )
        return [], "", ""

    # Multimodal upload handlers

    def handle_image_upload(image: Image.Image):
        if image is not None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            image_path = f"uploads/uploaded_image_{timestamp}.jpg"
            try:
                os.makedirs("uploads", exist_ok=True)
                image.save(image_path)
                log.info(f"Image uploaded and saved to {image_path}")
                return "User uploaded an image."
            except Exception as e:
                log.error(f"Error saving uploaded image: {e}")
                return "Failed to upload image."
        return ""

    def handle_video_upload(video):
        if video is not None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            video_path = f"uploads/uploaded_video_{timestamp}.mp4"
            try:
                os.makedirs("uploads", exist_ok=True)
                with open(video_path, "wb") as f:
                    f.write(video.read())
                log.info(f"Video uploaded and saved to {video_path}")
                return "User uploaded a video."
            except Exception as e:
                log.error(f"Error saving uploaded video: {e}")
                return "Failed to upload video."
        return ""

    def handle_audio_file_upload(audio_file):
        """Handle audio from gr.File (receives a file path string)."""
        if audio_file is not None:
            try:
                import shutil
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                audio_path = f"uploads/uploaded_audio_{timestamp}.wav"
                os.makedirs("uploads", exist_ok=True)
                src = audio_file.name if hasattr(audio_file, "name") else str(audio_file)
                shutil.copy2(src, audio_path)
                log.info(f"Audio file uploaded and saved to {audio_path}")
                return "User uploaded an audio file."
            except Exception as e:
                log.error(f"Error saving uploaded audio file: {e}")
                return "Failed to upload audio."
        return ""

    def handle_audio_record(audio):
        """Handle audio from gr.Audio (receives (sample_rate, np.ndarray) tuple)."""
        if audio is not None:
            try:
                sample_rate, audio_data = audio
                audio_data_normalized = audio_data.astype(np.float32) / max(np.abs(audio_data).max(), 1e-8)
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                audio_path = f"uploads/recorded_audio_{timestamp}.wav"
                os.makedirs("uploads", exist_ok=True)
                sf.write(audio_path, audio_data_normalized, sample_rate, subtype='PCM_16')
                log.info(f"Recorded audio saved to {audio_path}")
                return "User recorded an audio clip."
            except Exception as e:
                log.error(f"Error saving recorded audio: {e}")
                return "Failed to save recording."
        return ""

    def handle_upload(file):
        if file is None:
            return ""
        if file.type.startswith("image"):
            return handle_image_upload(file)
        elif file.type.startswith("video"):
            return handle_video_upload(file)
        elif file.type.startswith("audio"):
            return handle_audio_file_upload(file)
        else:
            log.warning(f"Unsupported file type uploaded: {file.type}")
            return "Unsupported file type uploaded."

    def clear_media():
        log.info("Cleared uploaded media paths.")
        return ""

    def bot(user_input, history, session_id):
        """Handle chatbot logic via ResponseQueueGateway."""
        if agent is None:
            log.error("Agent is not initialized.")
            history.append({"role": "assistant", "content": "Agent is not initialized."})
            yield history, '', session_id
            return

        try:
            if not session_id:
                session_id = uuid4().hex
                _emit_raw_memory(
                    "raw_memory.session.start",
                    {"session_id": session_id, "user_id": raw_user_id},
                )

            # Append user message
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": ""})
            yield history, '', session_id

            stream = (config_dict.get("llm_gateway_config") or {}).get("llm_stream", False)
            resp_timeout = float(
                (config_dict.get("gradio_config") or {}).get("response_timeout", 60.0)
            )

            # Emit input via gateway
            signal = queue_gateway.build_input_signal(
                user_input,
                source="perception.gradio",
                route=route_token,
            )
            trace_id = signal.trace_id
            asyncio.run_coroutine_threadsafe(
                queue_gateway.emit_input(
                    signal,
                    route=route_token,
                    add_pending_route=True,
                    event_name="perception.stimuli",
                ),
                agent.event_bus.loop,
            ).result(timeout=5)

            log.info(f"Emitted perception.stimuli for gradio input: {user_input[:80]}")

            assistant_message = ''
            if stream:
                while True:
                    try:
                        chunk = queue_gateway.get_for_trace(trace_id, resp_timeout)
                        if chunk == "<END_OF_RESPONSE>":
                            break
                        assistant_message += str(chunk)
                        new_history = list(history)
                        new_history[-1] = {"role": "assistant", "content": assistant_message}
                        yield new_history, '', session_id
                    except queue.Empty:
                        log.warning("Timeout: No response received from Agent.")
                        new_history = list(history)
                        new_history[-1] = {"role": "assistant", "content": "I'm sorry, I didn't receive a response in time."}
                        yield new_history, '', session_id
                        break
            else:
                try:
                    response = queue_gateway.get_for_trace(trace_id, resp_timeout)
                    assistant_message = str(response)
                except queue.Empty:
                    log.warning("Timeout: No response received from Agent.")
                    assistant_message = "I'm sorry, I didn't receive a response in time."
                new_history = list(history)
                new_history[-1] = {"role": "assistant", "content": assistant_message}
                yield new_history, '', session_id

        except Exception as e:
            log.error(f"Unexpected error in bot function: {e}")
            new_history = list(history)
            new_history[-1] = {"role": "assistant", "content": "An unexpected error occurred."}
            yield new_history, '', session_id

    # Build the Gradio interface

    with gr.Blocks(title="AEIVA Chat", css="""
        #chatbot { flex-grow: 1; overflow-y: auto; }
        .action-btn { min-width: 70px !important; }
        /* Keep the mic recorder compact */
        #audio-recorder { max-height: 80px; overflow: hidden; }
    """) as demo:
        # Compact header
        gr.HTML(
            "<div style='text-align:center; padding: 8px 0;'>"
            "<a href='https://github.com/chatsci/Aeiva'>"
            "<img src='https://i.ibb.co/P4zQHDk/aeiva-1024.png' "
            "alt='Aeiva' style='height:80px; vertical-align:middle;' /></a>"
            "&nbsp;&nbsp;"
            "<span style='font-size:1.4em; font-weight:600; vertical-align:middle;'>"
            "AEIVA: An Evolving Intelligent Virtual Assistant</span>"
            "<br/>"
            "<a href='https://github.com/chatsci/Aeiva'>"
            "<img src='https://img.shields.io/badge/Github-Code-blue'></a> "
            "<a href='https://arxiv.org/abs/2304.14178'>"
            "<img src='https://img.shields.io/badge/Arxiv-2304.14178-red'></a> "
            "<a href='https://github.com/chatsci/Aeiva/stargazers'>"
            "<img src='https://img.shields.io/github/stars/chatsci/Aeiva.svg?style=social'></a>"
            "</div>"
        )

        session_state = gr.State(value="")

        with gr.Row():
            # ---- Main chat area (dominant) ----
            with gr.Column(scale=3, min_width=400):
                chatbot = gr.Chatbot(
                    [], type="messages", elem_id="chatbot", height=550,
                )

                # Input row: textbox + upload button
                with gr.Row():
                    txt = gr.Textbox(
                        show_label=False,
                        placeholder="Type a message and press Enter ...",
                        lines=1,
                        scale=5,
                    )
                    btn = gr.UploadButton(
                        "Upload", file_types=["image", "video", "audio"],
                        scale=1,
                    )

                # Action buttons
                with gr.Row():
                    clear_history_btn = gr.Button("Clear History", size="sm", elem_classes=["action-btn"])
                    new_conv_btn = gr.Button("New Conversation", size="sm", elem_classes=["action-btn"])
                    del_last_turn_btn = gr.Button("Remove Last Turn", size="sm", elem_classes=["action-btn"])
                    regenerate_btn = gr.Button("Regenerate", size="sm", elem_classes=["action-btn"])

            # ---- Sidebar: settings & media (collapsible) ----
            with gr.Column(scale=1, min_width=250):
                with gr.Accordion("Parameters", open=False):
                    top_p = gr.Slider(
                        minimum=0, maximum=1.0, value=0.95, step=0.05,
                        interactive=True, label="Top-p",
                    )
                    temperature = gr.Slider(
                        minimum=0.1, maximum=2.0, value=1.0, step=0.1,
                        interactive=True, label="Temperature",
                    )
                    max_length_tokens = gr.Slider(
                        minimum=0, maximum=512, value=512, step=8,
                        interactive=True, label="Max Generation Tokens",
                    )
                    max_context_length_tokens = gr.Slider(
                        minimum=0, maximum=4096, value=2048, step=128,
                        interactive=True, label="Max History Tokens",
                    )

                with gr.Accordion("Media Uploads", open=False):
                    imagebox = gr.Image(type="pil", label="Image", height=120)
                    videobox = gr.File(label="Video File", file_types=["video"], height=60)
                    record_videobox = gr.Video(label="Record Video", height=120)
                    # Audio upload as a plain file picker (compact)
                    audiobox = gr.File(label="Audio File", file_types=["audio"], height=60)
                    # Mic recorder (constrained by CSS above)
                    record_audiobox = gr.Audio(
                        label="Record Audio",
                        sources=["microphone"],
                        type="numpy",
                        elem_id="audio-recorder",
                    )
                    clear_media_btn = gr.Button("Clear Media", variant="secondary", size="sm")

        # ---- Wire up interactions ----

        txt.submit(
            bot,
            inputs=[txt, chatbot, session_state],
            outputs=[chatbot, txt, session_state],
            queue=True,
        )

        btn.upload(handle_upload, inputs=btn, outputs=txt, queue=True)
        imagebox.upload(handle_image_upload, inputs=imagebox, outputs=txt, queue=True)
        videobox.upload(handle_video_upload, inputs=videobox, outputs=txt, queue=True)
        audiobox.upload(handle_audio_file_upload, inputs=audiobox, outputs=txt, queue=True)
        record_videobox.change(handle_video_upload, inputs=record_videobox, outputs=txt, queue=True)
        record_audiobox.change(handle_audio_record, inputs=record_audiobox, outputs=txt, queue=True)
        clear_media_btn.click(clear_media, inputs=None, outputs=None, queue=False)

        clear_history_btn.click(
            _end_session, inputs=session_state,
            outputs=[chatbot, txt, session_state], queue=False,
        )
        new_conv_btn.click(
            _end_session, inputs=session_state,
            outputs=[chatbot, txt, session_state], queue=False,
        )
        del_last_turn_btn.click(
            lambda history: history[:-2] if len(history) >= 2 else history,
            inputs=chatbot, outputs=chatbot, queue=False,
        )

        if hasattr(demo, "unload"):
            demo.unload(
                _end_session, inputs=session_state,
                outputs=[chatbot, txt, session_state], queue=False,
            )

    return demo
