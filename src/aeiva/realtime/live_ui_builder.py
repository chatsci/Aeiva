from __future__ import annotations

import asyncio
import inspect
import logging
import time
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from aeiva.realtime.live_ui_capabilities import LiveUICapabilities
from aeiva.liferpg.panel import build_liferpg_panel


_LIVE_UI_CSS = """
.aeiva-live-webrtc,
.aeiva-live-webrtc > div {
  max-height: 360px !important;
}
.aeiva-live-webrtc video {
  max-height: 360px !important;
  object-fit: cover !important;
}
"""


TextSubmitFn = Callable[[Any, str], Awaitable[Optional[str]]]
ImageCacheFn = Callable[[Any, Any], None]
ActiveHandlerFn = Callable[[], Any]


@dataclass
class LiveUIRuntime:
    provider_name: str
    title: str
    subtitle: str
    backend_label: str
    model_label: str
    notes: str
    capabilities: LiveUICapabilities
    handler: Any
    get_active_handler: ActiveHandlerFn
    submit_text: TextSubmitFn
    cache_uploaded_image: Optional[ImageCacheFn]
    logger: logging.Logger
    stream_handler: Any | None = None
    webrtc_variant: str = "wave"
    text_placeholder: str = "Type a message and press Enter"
    prefer_webrtc_video: bool = False
    webrtc_track_constraints: Optional[dict[str, Any]] = None
    config_dict: Optional[dict[str, Any]] = None


def _invoke_cache_image(cache_fn: Optional[ImageCacheFn], handler: Any, image: Any) -> None:
    if cache_fn is None:
        return
    try:
        cache_fn(handler, image)
    except Exception:
        # Upload cache errors should never tear down the UI callback loop.
        return


def _derive_webrtc_modality(
    cap: LiveUICapabilities,
    *,
    prefer_webrtc_video: bool = False,
) -> Optional[str]:
    has_audio = bool(cap.audio_input or cap.audio_output)
    has_video = bool(cap.video_input)
    if has_audio and has_video and prefer_webrtc_video:
        return "audio-video"
    if has_audio:
        return "audio"
    if has_video:
        return "video"
    return None


def _handler_is_available(handler: Any) -> bool:
    if handler is None:
        return False
    is_available = getattr(handler, "is_available", None)
    if callable(is_available):
        try:
            return bool(is_available())
        except Exception:
            return False
    if bool(getattr(handler, "_closed", False)):
        return False
    return True


def _resolve_handler_instance(runtime: LiveUIRuntime) -> Any:
    active_handler = None
    try:
        active_handler = runtime.get_active_handler() if callable(runtime.get_active_handler) else None
    except Exception:
        active_handler = None
    if _handler_is_available(active_handler):
        return active_handler
    if _handler_is_available(runtime.handler):
        return runtime.handler
    return active_handler or runtime.handler


def _iter_handler_cache_targets(runtime: LiveUIRuntime) -> list[Any]:
    """
    Return handler instances that should receive uploaded image / webcam frames.

    In live WebRTC mode FastRTC may clone handlers per connection. Caching to
    both active and base handlers avoids frame loss when connection lifecycle
    switches active instances.
    """
    targets: list[Any] = []
    seen_ids: set[int] = set()
    try:
        active_handler = runtime.get_active_handler() if callable(runtime.get_active_handler) else None
    except Exception:
        active_handler = None
    for candidate in (active_handler, runtime.handler):
        if candidate is None:
            continue
        candidate_id = id(candidate)
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        targets.append(candidate)
    return targets


def _cache_camera_frame_for_webrtc(frame: Any, *, runtime: LiveUIRuntime) -> Any:
    if frame is None:
        return None
    for handler_instance in _iter_handler_cache_targets(runtime):
        _invoke_cache_image(runtime.cache_uploaded_image, handler_instance, frame)
    # Keep local/remote preview stable in send mode by preserving the frame.
    return frame


def _derive_webrtc_mode(cap: LiveUICapabilities) -> str:
    if cap.audio_output:
        return "send-receive"
    return "send"


def _default_webrtc_track_constraints(modality: Optional[str]) -> Optional[dict[str, Any]]:
    if modality == "audio":
        return {
            "echoCancellation": True,
            "noiseSuppression": True,
            "autoGainControl": True,
            "channelCount": 1,
        }
    if modality == "video":
        return {
            "facingMode": "user",
            "width": {"ideal": 960},
            "height": {"ideal": 540},
            "frameRate": {"ideal": 24, "max": 30},
        }
    if modality == "audio-video":
        return {
            "video": {
                "facingMode": "user",
                "width": {"ideal": 960},
                "height": {"ideal": 540},
                "frameRate": {"ideal": 24, "max": 30},
            },
            "audio": {
                "echoCancellation": True,
                "noiseSuppression": True,
                "autoGainControl": True,
                "channelCount": 1,
            },
        }
    return None


def _normalize_webrtc_track_constraints(
    modality: Optional[str],
    constraints: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    if not isinstance(constraints, dict):
        return constraints
    if modality == "audio":
        nested_audio = constraints.get("audio")
        if isinstance(nested_audio, dict):
            return dict(nested_audio)
    if modality == "video":
        nested_video = constraints.get("video")
        if isinstance(nested_video, dict):
            return dict(nested_video)
    return constraints


def _describe_capability_summary(cap: LiveUICapabilities) -> str:
    inputs = ", ".join(cap.enabled_inputs()) or "none"
    duplex = "enabled" if cap.duplex else "disabled"
    return f"**Inputs:** `{inputs}`  \n**Duplex:** `{duplex}`"


async def _collect_text_reply_from_handler_queue(
    handler: Any,
    *,
    timeout: float,
) -> Optional[str]:
    queue_obj = getattr(handler, "text_queue", None)
    if not isinstance(queue_obj, asyncio.Queue):
        return None
    chunks: list[str] = []
    deadline = time.monotonic() + max(0.1, float(timeout))
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        wait_timeout = min(0.35, remaining)
        try:
            chunk = await asyncio.wait_for(queue_obj.get(), timeout=wait_timeout)
        except asyncio.TimeoutError:
            if chunks:
                break
            continue
        if chunk == "<END_OF_RESPONSE>":
            break
        if chunk is None:
            continue
        chunks.append(str(chunk))
    text = "".join(chunks).strip()
    return text or None


def build_multimodal_stream_ui(*, gr: Any, WebRTC: Any, runtime: LiveUIRuntime, realtime_cfg: dict) -> Any:
    cap = runtime.capabilities
    webrtc_modality = _derive_webrtc_modality(cap, prefer_webrtc_video=runtime.prefer_webrtc_video)
    webrtc_mode = _derive_webrtc_mode(cap)
    webrtc_handles_video = webrtc_modality in {"video", "audio-video"}
    video_input_transport = str(realtime_cfg.get("video_input_transport", "image")).strip().lower()

    with gr.Blocks(title=runtime.title, css=_LIVE_UI_CSS) as demo:
        gr.HTML(
            f"<h1 style='text-align:center;'>{runtime.title}</h1>"
            f"<p style='text-align:center;'>{runtime.subtitle}</p>"
        )
        tabs_ctx = gr.Tabs() if hasattr(gr, "Tabs") else nullcontext()
        stream_tab_ctx = gr.Tab("Stream") if hasattr(gr, "Tab") else nullcontext()
        with tabs_ctx:
            with stream_tab_ctx:
                with gr.Row():
                    with gr.Column(scale=1, min_width=360):
                        gr.Markdown("### Settings")
                        gr.Markdown("**Mode:** `live`")
                        gr.Markdown(f"**Provider:** `{runtime.provider_name}`")
                        gr.Markdown(f"**Backend:** `{runtime.backend_label}`")
                        gr.Markdown(f"**Model:** `{runtime.model_label}`")
                        gr.Markdown(_describe_capability_summary(cap))

                        camera_input = None
                        camera_webrtc = None
                        camera_stream_handler = None
                        if cap.video_input and not webrtc_handles_video:
                            if video_input_transport == "webrtc":
                                try:
                                    from fastrtc import VideoStreamHandler

                                    def _cache_camera_frame_webrtc(frame, *_args):
                                        return _cache_camera_frame_for_webrtc(frame, runtime=runtime)

                                    camera_track_constraints = _default_webrtc_track_constraints("video")
                                    camera_webrtc = WebRTC(
                                        modality="video",
                                        mode="send",
                                        full_screen=False,
                                        height=240,
                                        variant=runtime.webrtc_variant,
                                        track_constraints=camera_track_constraints,
                                        elem_classes="aeiva-live-webrtc",
                                    )
                                    camera_stream_handler = VideoStreamHandler(
                                        _cache_camera_frame_webrtc,
                                        fps=max(1, int(realtime_cfg.get("video_webrtc_fps", 6))),
                                        skip_frames=True,
                                    )
                                except Exception as e:
                                    runtime.logger.warning(
                                        "Video WebRTC transport init failed, fallback to Image webcam: %s",
                                        e,
                                    )
                                    video_input_transport = "image"

                            if video_input_transport != "webrtc":
                                camera_input = gr.Image(
                                    label="Webcam (live)",
                                    type="numpy",
                                    sources=["webcam"],
                                    streaming=True,
                                    height=240,
                                )

                                def _cache_camera_frame(frame):
                                    if frame is None:
                                        return
                                    for handler_instance in _iter_handler_cache_targets(runtime):
                                        _invoke_cache_image(runtime.cache_uploaded_image, handler_instance, frame)

                                camera_stream_every = float(realtime_cfg.get("video_stream_every", 1.0))
                                if camera_stream_every <= 0:
                                    camera_stream_every = 1.0
                                camera_stream_queue = bool(realtime_cfg.get("video_stream_queue", True))
                                camera_stream_concurrency = int(realtime_cfg.get("video_stream_concurrency_limit", 1))
                                if camera_stream_concurrency <= 0:
                                    camera_stream_concurrency = 1

                                camera_input.stream(
                                    _cache_camera_frame,
                                    inputs=camera_input,
                                    outputs=None,
                                    queue=camera_stream_queue,
                                    show_progress="hidden",
                                    stream_every=camera_stream_every,
                                    trigger_mode="always_last",
                                    concurrency_limit=camera_stream_concurrency,
                                )

                        upload_image = None
                        if cap.image_input:
                            upload_image = gr.Image(
                                label="Upload / Paste Image",
                                type="numpy",
                                sources=["upload", "clipboard"],
                                height=170,
                            )

                            def _cache_uploaded_image(image):
                                if image is None:
                                    return None
                                for handler_instance in _iter_handler_cache_targets(runtime):
                                    _invoke_cache_image(runtime.cache_uploaded_image, handler_instance, image)
                                return None

                            upload_image.change(
                                _cache_uploaded_image,
                                inputs=upload_image,
                                outputs=None,
                                queue=False,
                                show_progress=False,
                            )

                        if cap.file_input:
                            gr.File(label="Upload File", file_count="multiple")

                        webrtc = None
                        if webrtc_modality is not None:
                            raw_constraints = runtime.webrtc_track_constraints or _default_webrtc_track_constraints(
                                webrtc_modality
                            )
                            track_constraints = _normalize_webrtc_track_constraints(
                                webrtc_modality,
                                raw_constraints,
                            )
                            webrtc = WebRTC(
                                modality=webrtc_modality,
                                mode=webrtc_mode,
                                full_screen=False,
                                height=360,
                                variant=runtime.webrtc_variant,
                                track_constraints=track_constraints,
                                elem_classes="aeiva-live-webrtc",
                            )

                        gr.Markdown(runtime.notes)

                    with gr.Column(scale=2, min_width=520):
                        chatbot = gr.Chatbot(type="messages", height=600)

                        txt = None
                        if cap.text_input:
                            with gr.Row():
                                txt = gr.Textbox(
                                    show_label=False,
                                    placeholder=runtime.text_placeholder,
                                    lines=1,
                                    scale=4,
                                )

                    async def text_submit(user_text, history):
                        if not user_text or not user_text.strip():
                            return history, ""
                        history = list(history) if history else []
                        text = str(user_text).strip()
                        history.append({"role": "user", "content": text})
                        handler_instance = _resolve_handler_instance(runtime)
                        if hasattr(handler_instance, "chatbot"):
                            handler_instance.chatbot = list(history)
                        try:
                            submit_timeout = float(
                                realtime_cfg.get(
                                    "text_submit_timeout",
                                    realtime_cfg.get("text_response_timeout", 12.0),
                                )
                            )
                            reply = await asyncio.wait_for(
                                runtime.submit_text(handler_instance, text),
                                timeout=max(1.0, submit_timeout),
                            )
                            if (
                                isinstance(reply, str)
                                and reply.startswith("[MiniCPM text fallback error]")
                                and handler_instance is not runtime.handler
                                and _handler_is_available(runtime.handler)
                            ):
                                retry_reply = await asyncio.wait_for(
                                    runtime.submit_text(runtime.handler, text),
                                    timeout=max(1.0, submit_timeout),
                                )
                                if isinstance(retry_reply, str) and retry_reply.strip():
                                    reply = retry_reply
                            if reply is None and (webrtc is None or not cap.audio_output):
                                reply = await _collect_text_reply_from_handler_queue(
                                    handler_instance,
                                    timeout=float(realtime_cfg.get("text_response_timeout", 30.0)),
                                )
                            if isinstance(reply, str) and reply.strip():
                                history.append({"role": "assistant", "content": reply.strip()})
                        except asyncio.TimeoutError:
                            history.append(
                                {
                                    "role": "assistant",
                                    "content": "[Text request timeout] backend did not return within configured timeout.",
                                }
                            )
                        except Exception as e:
                            runtime.logger.error("Live text submit failed: %s", e)
                            history.append({"role": "assistant", "content": f"Error: {e}"})
                        if hasattr(handler_instance, "chatbot"):
                            handler_instance.chatbot = list(history)
                        return history, ""

                    txt.submit(
                        text_submit,
                        inputs=[txt, chatbot],
                        outputs=[chatbot, txt],
                        queue=False,
                    )

                    with gr.Row():
                        clear_btn = gr.Button("Clear History")
                    if txt is not None:
                        clear_btn.click(lambda: ([], ""), outputs=[chatbot, txt], queue=False)
                    else:
                        clear_btn.click(lambda: [], outputs=[chatbot], queue=False)

                    if webrtc is not None:
                        webrtc_time_limit = int(realtime_cfg.get("webrtc_time_limit", 90))
                        stream_handler = runtime.stream_handler or runtime.handler
                        webrtc.stream(
                            stream_handler,
                            inputs=[webrtc],
                            outputs=[webrtc],
                            time_limit=webrtc_time_limit,
                            send_input_on="submit",
                        )
                        webrtc.on_additional_outputs(
                            lambda old, new: new,
                            inputs=[chatbot],
                            outputs=[chatbot],
                            queue=False,
                        )
                    if camera_webrtc is not None and camera_stream_handler is not None:
                        camera_webrtc.stream(
                            camera_stream_handler,
                            inputs=[camera_webrtc],
                            outputs=[camera_webrtc],
                            time_limit=int(realtime_cfg.get("video_webrtc_time_limit", 90)),
                            send_input_on="change",
                        )

            if hasattr(gr, "Tab"):
                build_liferpg_panel(gr=gr, config_dict=runtime.config_dict or {})

    return demo


async def default_submit_text(handler: Any, text: str) -> Optional[str]:
    send_text = getattr(handler, "send_text", None)
    if not callable(send_text):
        return None
    result = send_text(text)
    if inspect.isawaitable(result):
        result = await result
    if isinstance(result, str):
        return result
    return None
