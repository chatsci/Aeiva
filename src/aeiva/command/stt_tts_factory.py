"""
STT/TTS factory for realtime mode (FastRTC only).

Supported backend:
    - ``"fastrtc"`` (default) — Moonshine STT + Kokoro TTS
"""

from typing import Any


def create_stt_model(realtime_cfg: dict) -> Any:
    """Create an STT model from *realtime_cfg*."""
    stt_cfg = realtime_cfg.get("stt", {})
    backend = stt_cfg.get("backend", "fastrtc")
    if backend != "fastrtc":
        raise ValueError(f"Unsupported STT backend: {backend!r}")
    model_name = stt_cfg.get("fastrtc", {}).get("model", "moonshine/base")
    from fastrtc import get_stt_model
    return get_stt_model(model_name)


def create_tts_model(realtime_cfg: dict) -> Any:
    """Create a TTS model from *realtime_cfg*."""
    tts_cfg = realtime_cfg.get("tts", {})
    backend = tts_cfg.get("backend", "fastrtc")
    if backend != "fastrtc":
        raise ValueError(f"Unsupported TTS backend: {backend!r}")
    model_name = tts_cfg.get("fastrtc", {}).get("model", "kokoro")
    from fastrtc import get_tts_model
    return get_tts_model(model_name)
