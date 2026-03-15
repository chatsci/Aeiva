from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator, Tuple

import numpy as np


logger = logging.getLogger(__name__)


@contextmanager
def _temporary_env(name: str, value: str) -> Iterator[None]:
    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


class EnergyPauseDetectionModel:
    """
    Lightweight local VAD fallback with no network/model dependency.

    It estimates voiced duration by amplitude thresholding. This is intentionally
    simple and only used when Silero is unavailable.
    """

    def __init__(self, *, threshold: float = 0.015):
        self.threshold = float(max(1e-4, threshold))

    def warmup(self) -> None:
        return

    def vad(
        self,
        audio: Tuple[int, np.ndarray[Any, np.dtype[np.int16]] | np.ndarray[Any, np.dtype[np.float32]]],
        options: Any,
    ) -> tuple[float, list[Any]]:
        sample_rate, samples = audio
        if sample_rate <= 0:
            return 0.0, []
        arr = np.asarray(samples)
        if arr.size == 0:
            return 0.0, []
        if arr.ndim > 1:
            arr = np.mean(arr, axis=1)
        arr = arr.astype(np.float32, copy=False)
        if np.max(np.abs(arr)) > 1.0:
            arr = arr / 32768.0

        threshold = self.threshold
        opt_threshold = getattr(options, "threshold", None)
        if isinstance(opt_threshold, (int, float)) and opt_threshold > 0:
            # Silero threshold defaults around 0.5; map to an amplitude band.
            threshold = max(threshold, float(opt_threshold) * 0.03)

        voiced_samples = np.count_nonzero(np.abs(arr) >= threshold)
        return float(voiced_samples) / float(sample_rate), []


def build_pause_detection_model(realtime_cfg: dict | None, *, log: logging.Logger | None = None) -> Any:
    """
    Build pause detection model used by FastRTC ReplyOnPause.

    Config keys under ``realtime_config``:
      - pause_detection_model: ``energy`` | ``silero`` | ``auto`` (default: energy)
      - silero_offline_only: bool (default: true)
      - energy_vad_threshold: float (default: 0.015)
    """

    logger_obj = log or logger
    cfg = realtime_cfg or {}
    mode = str(cfg.get("pause_detection_model", "energy")).strip().lower() or "energy"
    if mode not in {"auto", "silero", "energy"}:
        mode = "energy"
    silero_offline_only = bool(cfg.get("silero_offline_only", True))
    energy_threshold = float(cfg.get("energy_vad_threshold", 0.015))

    if mode in {"auto", "silero"}:
        try:
            from fastrtc.pause_detection.silero import get_silero_model

            if silero_offline_only:
                with _temporary_env("HF_HUB_OFFLINE", "1"):
                    model = get_silero_model()
            else:
                model = get_silero_model()
            logger_obj.info("Using Silero pause detection model.")
            return model
        except Exception as exc:
            if mode == "silero":
                raise
            logger_obj.warning(
                "Silero pause detection unavailable (%s); falling back to energy VAD.",
                exc,
            )

    logger_obj.info("Using energy pause detection fallback model.")
    return EnergyPauseDetectionModel(threshold=energy_threshold)
