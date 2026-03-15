from __future__ import annotations

import importlib.metadata as metadata
from urllib.parse import urlparse
from typing import Any, Dict

import httpx

from aeiva.realtime.live_ui_builder import (
    LiveUIRuntime,
    build_multimodal_stream_ui,
    default_submit_text,
)
from aeiva.realtime.live_ui_capabilities import LiveUICapabilities, resolve_live_ui_capabilities
from aeiva.realtime.minicpm_live_client import MiniCPMLiveConfig, MiniCPMOmniRealtimeHandler
from aeiva.realtime.providers.base import LiveRealtimeProvider


class MiniCPMLiveProvider(LiveRealtimeProvider):
    """
    Live provider for local MiniCPM Omni HTTP backend.

    Default target: WebRTC_Demo C++ wrapper service (`http://127.0.0.1:9060`).
    """

    provider_name = "minicpm_local"

    @staticmethod
    def _dedupe_candidates(candidates: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate or "").strip().rstrip("/")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(key)
        return deduped

    @staticmethod
    def _probe_omni_api_ready(base_url: str, timeout: float) -> bool:
        try:
            with httpx.Client(
                timeout=max(0.2, float(timeout)),
                headers={"Connection": "close"},
            ) as client:
                # Probe a real omni API endpoint instead of /health.
                # /health may be served by auxiliary sidecar ports (e.g. 9061)
                # that do not expose /omni/init_sys_prompt and will break media flow.
                probe_url = f"{base_url.rstrip('/')}/omni/init_sys_prompt"
                resp = client.get(probe_url)
                status = int(resp.status_code)
                # 405 means endpoint exists but method is not allowed (expected for GET).
                # 404 means wrong port/service.
                if status == 404:
                    return False
                if status >= 500:
                    return False
                return True
        except Exception:
            return False

    def _build_omni_probe_candidates(
        self,
        *,
        base_url: str,
        extra_ports: int,
    ) -> list[str]:
        normalized_base = str(base_url or "").strip().rstrip("/")
        if not normalized_base:
            return []

        candidates = [normalized_base]
        parsed = urlparse(normalized_base)
        if not parsed.hostname or not parsed.port:
            return candidates

        scheme = parsed.scheme or "http"
        host = parsed.hostname
        current_port = int(parsed.port)
        max_extra_ports = max(0, int(extra_ports))
        for offset in range(1, max_extra_ports + 1):
            shifted = f"{scheme}://{host}:{current_port + offset}"
            candidates.append(shifted)
        return self._dedupe_candidates(candidates)

    def _resolve_reachable_omni_base_url(
        self,
        *,
        live_config: MiniCPMLiveConfig,
        minicpm_cfg: Dict[str, Any],
    ) -> None:
        probe_timeout = float(minicpm_cfg.get("startup_probe_timeout", 1.2))
        extra_ports = int(minicpm_cfg.get("startup_probe_extra_ports", 0))
        strict = bool(minicpm_cfg.get("startup_probe_strict", False))
        candidates = self._build_omni_probe_candidates(
            base_url=live_config.base_url,
            extra_ports=extra_ports,
        )

        for candidate in candidates:
            if self._probe_omni_api_ready(candidate, timeout=probe_timeout):
                normalized = candidate.rstrip("/")
                if normalized != live_config.base_url.rstrip("/"):
                    self.logger.warning(
                        "MiniCPM omni base_url %s unreachable; auto-switched to %s",
                        live_config.base_url,
                        normalized,
                    )
                live_config.base_url = normalized
                return

        message = (
            "MiniCPM omni backend probe failed. "
            f"Tried {len(candidates)} candidate(s) from base_url={live_config.base_url}. "
            "Will keep configured base_url; if realtime media has no response, restart oneclick services."
        )
        if strict:
            raise RuntimeError(message)
        self.logger.warning(message)

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
            "Ensure `fastrtc` is installed and environment dependencies are synced. "
            "Run: `uv sync --all-extras`."
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

    def _build_live_config(self) -> tuple[MiniCPMLiveConfig, Dict[str, Any]]:
        minicpm_cfg: Dict[str, Any] = self.realtime_cfg.get("minicpm", {}) or {}
        return MiniCPMLiveConfig(
            base_url=str(minicpm_cfg.get("base_url") or "http://127.0.0.1:9060").rstrip("/"),
            language=str(minicpm_cfg.get("language") or "zh"),
            duplex_mode=bool(minicpm_cfg.get("duplex_mode", True)),
            high_quality_mode=bool(minicpm_cfg.get("high_quality_mode", False)),
            high_fps_mode=bool(minicpm_cfg.get("high_fps_mode", False)),
            send_video=bool(minicpm_cfg.get("send_video", True)),
            video_fps=float(minicpm_cfg.get("video_fps", 1.0)),
            output_sample_rate=int(minicpm_cfg.get("output_sample_rate", 24000)),
            output_frame_size=int(minicpm_cfg.get("output_frame_size", 960)),
            input_sample_rate=int(minicpm_cfg.get("input_sample_rate", 24000)),
            prefill_audio_chunk_ms=int(minicpm_cfg.get("prefill_audio_chunk_ms", 240)),
            request_timeout=float(minicpm_cfg.get("request_timeout", 20.0)),
            auto_break_on_barge_in=bool(minicpm_cfg.get("auto_break_on_barge_in", True)),
            prefill_flush_idle_ms=int(minicpm_cfg.get("prefill_flush_idle_ms", 180)),
            text_fallback_enabled=bool(minicpm_cfg.get("text_fallback_enabled", True)),
            text_fallback_base_url=str(
                minicpm_cfg.get("text_fallback_base_url") or "http://127.0.0.1:19060/v1"
            ).rstrip("/"),
            text_fallback_model=str(minicpm_cfg.get("text_fallback_model") or "openbmb/MiniCPM-o-4_5"),
            text_fallback_timeout=float(minicpm_cfg.get("text_fallback_timeout", 30.0)),
            text_fallback_retries=int(minicpm_cfg.get("text_fallback_retries", 3)),
            text_fallback_retry_backoff_seconds=float(
                minicpm_cfg.get("text_fallback_retry_backoff_seconds", 0.4)
            ),
            text_fallback_allow_direct_port_discovery=bool(
                minicpm_cfg.get("text_fallback_allow_direct_port_discovery", False)
            ),
            service_registry_enabled=bool(minicpm_cfg.get("service_registry_enabled", True)),
            init_retries=int(minicpm_cfg.get("init_retries", 3)),
            init_retry_backoff_seconds=float(minicpm_cfg.get("init_retry_backoff_seconds", 0.6)),
        ), minicpm_cfg

    def _resolve_capabilities(
        self,
        *,
        live_config: MiniCPMLiveConfig,
        minicpm_cfg: Dict[str, Any],
    ) -> LiveUICapabilities:
        defaults = LiveUICapabilities(
            text_input=True,
            text_output=True,
            audio_input=True,
            audio_output=True,
            video_input=bool(live_config.send_video),
            image_input=True,
            file_input=False,
            duplex=bool(live_config.duplex_mode),
        )
        return resolve_live_ui_capabilities(
            realtime_cfg=self.realtime_cfg,
            provider_cfg=minicpm_cfg,
            defaults=defaults,
        )

    def build_demo(self):
        gr, WebRTC = self._import_ui()
        live_config, minicpm_cfg = self._build_live_config()
        self._resolve_reachable_omni_base_url(
            live_config=live_config,
            minicpm_cfg=minicpm_cfg,
        )
        handler = MiniCPMOmniRealtimeHandler(live_config)
        capabilities = self._resolve_capabilities(
            live_config=live_config,
            minicpm_cfg=minicpm_cfg,
        )

        async def _submit_text_via_base_handler(_active_handler: Any, text: str):
            # Keep text fallback routed through the stable base handler so text
            # interactions remain available even when transient WebRTC clones
            # disconnect or restart.
            return await default_submit_text(handler, text)

        runtime = LiveUIRuntime(
            provider_name=self.provider_name,
            title="AEIVA Multimodal Stream UI",
            subtitle="Capability-driven realtime interface",
            backend_label=live_config.base_url,
            model_label=live_config.text_fallback_model,
            notes=(
                "*MiniCPM omni transport for streaming media. "
                "Text input uses OpenAI-compatible fallback endpoint when enabled.*"
            ),
            capabilities=capabilities,
            handler=handler,
            get_active_handler=lambda: MiniCPMOmniRealtimeHandler.get_active(),
            submit_text=_submit_text_via_base_handler,
            cache_uploaded_image=lambda h, image: h.update_latest_frame(image)
            if hasattr(h, "update_latest_frame")
            else None,
            logger=self.logger,
            # Default to a single audio-video WebRTC stream to avoid
            # cross-component device/stream conflicts in browser runtime.
            prefer_webrtc_video=bool(minicpm_cfg.get("prefer_webrtc_video", True)),
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
        if bool(launch_kwargs.get("share", False)):
            self.logger.warning(
                "realtime_config.share=true may degrade local WebRTC media stability for MiniCPM. "
                "Prefer local URL with share=false for full-duplex audio/video."
            )
        self.logger.info(
            "Launching live realtime Gradio interface (provider=%s, backend=%s)...",
            self.provider_name,
            self._build_live_config()[0].base_url,
        )
        self._launch_demo_with_recovery(demo, launch_kwargs)
