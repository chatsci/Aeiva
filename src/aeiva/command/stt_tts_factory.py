"""
STT/TTS factory for realtime mode (FastRTC only).

Supported backend:
    - ``"fastrtc"`` (default) — Moonshine STT + Kokoro TTS
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_load_mode(realtime_cfg: dict) -> str:
    raw = (realtime_cfg or {}).get("model_load_mode", "lazy")
    mode = str(raw).strip().lower()
    if mode not in {"lazy", "eager"}:
        return "lazy"
    return mode


class _LazyModelLoader:
    def __init__(self, *, loader, model_kind: str, model_name: str):
        self._loader = loader
        self._model_kind = model_kind
        self._model_name = model_name
        self._lock = threading.Lock()
        self._model: Any = None
        self._load_error: Exception | None = None

    def _ensure_loaded(self) -> Any:
        if self._model is not None:
            return self._model
        if self._load_error is not None:
            return None
        with self._lock:
            if self._model is not None:
                return self._model
            if self._load_error is not None:
                return None
            try:
                self._model = self._loader()
                logger.info(
                    "Loaded %s model on demand: %s",
                    self._model_kind,
                    self._model_name,
                )
            except Exception as exc:
                self._load_error = exc
                logger.warning(
                    "Failed to lazy-load %s model %s: %s",
                    self._model_kind,
                    self._model_name,
                    exc,
                )
                return None
        return self._model


class LazySTTModel(_LazyModelLoader):
    def stt(self, audio: Any) -> str:
        model = self._ensure_loaded()
        if model is None:
            return ""
        return str(model.stt(audio) or "")


class LazyTTSModel(_LazyModelLoader):
    def stream_tts_sync(self, text: str):
        model = self._ensure_loaded()
        if model is None:
            return
            yield  # pragma: no cover
        yield from model.stream_tts_sync(text)


def create_stt_model(realtime_cfg: dict) -> Any:
    """Create an STT model from *realtime_cfg*."""
    stt_cfg = realtime_cfg.get("stt", {})
    backend = stt_cfg.get("backend", "fastrtc")
    if backend != "fastrtc":
        raise ValueError(f"Unsupported STT backend: {backend!r}")
    model_name = stt_cfg.get("fastrtc", {}).get("model", "moonshine/base")

    def _loader():
        from fastrtc import get_stt_model
        return get_stt_model(model_name)

    if _normalize_load_mode(realtime_cfg) == "lazy":
        logger.info("Using lazy STT model loading: %s", model_name)
        return LazySTTModel(loader=_loader, model_kind="STT", model_name=model_name)
    return _loader()


def create_tts_model(realtime_cfg: dict) -> Any:
    """Create a TTS model from *realtime_cfg*."""
    tts_cfg = realtime_cfg.get("tts", {})
    backend = tts_cfg.get("backend", "fastrtc")
    if backend != "fastrtc":
        raise ValueError(f"Unsupported TTS backend: {backend!r}")
    model_name = tts_cfg.get("fastrtc", {}).get("model", "kokoro")

    def _loader():
        from fastrtc import get_tts_model
        return get_tts_model(model_name)

    if _normalize_load_mode(realtime_cfg) == "lazy":
        logger.info("Using lazy TTS model loading: %s", model_name)
        return LazyTTSModel(loader=_loader, model_kind="TTS", model_name=model_name)
    return _loader()
