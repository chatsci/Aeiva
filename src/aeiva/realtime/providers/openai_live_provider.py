from __future__ import annotations

import os
import importlib.metadata as metadata
from typing import Any, Dict

from aeiva.realtime.live_ui_builder import (
    LiveUIRuntime,
    build_multimodal_stream_ui,
    default_submit_text,
)
from aeiva.realtime.live_ui_capabilities import LiveUICapabilities, resolve_live_ui_capabilities
from aeiva.realtime.providers.base import LiveRealtimeProvider


class OpenAILiveProvider(LiveRealtimeProvider):
    """
    Live provider backed by OpenAI Realtime-compatible WebSocket transport.
    """

    provider_name = "openai"

    @staticmethod
    def _build_realtime_import_error(raw_error: Exception) -> RuntimeError:
        def _safe_version(name: str) -> str:
            try:
                return metadata.version(name)
            except Exception:
                return "not-installed"

        gradio_version = _safe_version("gradio")
        webrtc_version = _safe_version("gradio-webrtc")
        message = (
            "Live realtime UI import failed. "
            f"Detected gradio={gradio_version}, gradio-webrtc={webrtc_version}. "
            "This is usually a dependency mismatch for realtime UI components."
        )
        error = RuntimeError(message)
        error.__cause__ = raw_error
        return error

    def _import_ui(self):
        try:
            import gradio as gr
            from fastrtc import WebRTC as FastRTCWebRTC
            from aeiva.realtime.fastrtc_webrtc import build_safe_webrtc_component

            WebRTC = build_safe_webrtc_component(FastRTCWebRTC)
            return gr, WebRTC
        except ImportError as e:
            raise self._build_realtime_import_error(e)

    def _resolve_api_key(self) -> str:
        llm_cfg = self.config_dict.get("llm_gateway_config", {}) or {}
        api_key = str(llm_cfg.get("llm_api_key") or "").strip()
        if not api_key:
            env_var = str(llm_cfg.get("llm_api_key_env_var") or "").strip()
            if env_var:
                api_key = str(os.getenv(env_var, "")).strip()
        if not api_key:
            raise RuntimeError("OpenAI API key is required for live realtime mode.")
        return api_key

    def _build_live_config(self):
        from aeiva.realtime.openai_realtime import OpenAIRealtimeConfig

        api_key = self._resolve_api_key()
        openai_cfg: Dict[str, Any] = self.realtime_cfg.get("openai", {}) or {}
        return OpenAIRealtimeConfig(
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
        ), openai_cfg

    def _build_handler(self) -> tuple[Any, Any, Dict[str, Any]]:
        from aeiva.realtime.openai_realtime import OpenAIRealtimeHandler

        live_config, openai_cfg = self._build_live_config()
        handler = OpenAIRealtimeHandler(live_config)
        return handler, live_config, openai_cfg

    def _resolve_capabilities(self, *, live_config: Any, openai_cfg: Dict[str, Any]) -> LiveUICapabilities:
        defaults = LiveUICapabilities(
            text_input=True,
            text_output=True,
            audio_input=True,
            audio_output=True,
            video_input=bool(live_config.send_video),
            image_input=bool(live_config.send_video),
            file_input=False,
            duplex=True,
        )
        return resolve_live_ui_capabilities(
            realtime_cfg=self.realtime_cfg,
            provider_cfg=openai_cfg,
            defaults=defaults,
        )

    def build_demo(self):
        gr, WebRTC = self._import_ui()
        handler, live_config, openai_cfg = self._build_handler()
        capabilities = self._resolve_capabilities(
            live_config=live_config,
            openai_cfg=openai_cfg,
        )

        from aeiva.realtime.openai_realtime import OpenAIRealtimeHandler

        runtime = LiveUIRuntime(
            provider_name=self.provider_name,
            title="AEIVA Multimodal Stream UI",
            subtitle="Capability-driven realtime interface",
            backend_label=live_config.base_url,
            model_label=live_config.model,
            notes=(
                "*OpenAI-compatible live transport. "
                "Controls are enabled according to resolved capability profile.*"
            ),
            capabilities=capabilities,
            handler=handler,
            get_active_handler=lambda: OpenAIRealtimeHandler.get_active(),
            submit_text=default_submit_text,
            cache_uploaded_image=lambda h, image: getattr(h, "update_latest_frame")(image)
            if hasattr(h, "update_latest_frame")
            else None,
            logger=self.logger,
            prefer_webrtc_video=True,
            config_dict=self.config_dict,
        )
        return build_multimodal_stream_ui(
            gr=gr,
            WebRTC=WebRTC,
            runtime=runtime,
            realtime_cfg=self.realtime_cfg,
        )

    def launch(self, *, prevent_thread_lock: bool = False) -> None:
        demo = self.build_demo()
        launch_kwargs = self._build_gradio_launch_kwargs(
            prevent_thread_lock=prevent_thread_lock
        )
        self.logger.info("Launching live realtime Gradio interface (provider=%s)...", self.provider_name)
        self._launch_demo_with_recovery(demo, launch_kwargs)
