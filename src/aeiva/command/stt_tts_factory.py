"""
STT/TTS factory: selects backend based on ``realtime_config.stt.backend``
and ``realtime_config.tts.backend``.

Supported backends:
    - ``"fastrtc"`` (default) — FastRTC Moonshine STT + Kokoro TTS
    - ``"mlx"``               — mlx-audio Whisper STT + Kokoro TTS (Apple Silicon)

Both backends expose the same duck-typed interface consumed by
``RealtimePipelineHandler``:
    stt_model.stt((sample_rate, np.ndarray)) -> str
    tts_model.stream_tts_sync(text) -> Generator[(sample_rate, np.ndarray)]
"""

import logging
import re
from typing import Any, Generator, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_KOKORO_LANG_CODES = {"a", "b", "e", "f", "h", "i", "p", "j", "z"}
_KOKORO_LANG_ALIASES = {
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr-fr": "f",
    "hi": "h",
    "it": "i",
    "pt-br": "p",
    "ja": "j",
    "zh": "z",
    "en": "a",
    "fr": "f",
}
_DEFAULT_VOICE_MAP = {
    "a": "af_heart",
    "f": "ff_siwis",
    "z": "zf_xiaobei",
}
_AUTO_LANG_TOKENS = {"auto", "detect", "autodetect"}
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_FRENCH_CHARS_RE = re.compile(r"[àâäçéèêëîïôöùûüÿœæ]", re.IGNORECASE)
_FRENCH_WORDS = {
    "le",
    "la",
    "les",
    "des",
    "du",
    "de",
    "un",
    "une",
    "et",
    "est",
    "pas",
    "que",
    "qui",
    "pour",
    "avec",
    "mais",
    "dans",
    "sur",
    "au",
    "aux",
    "ce",
    "cette",
}


def _normalize_kokoro_lang_code(lang_code: Optional[str]) -> Optional[str]:
    """Normalize Kokoro language codes and aliases."""
    if not lang_code:
        return None
    code = lang_code.strip().lower()
    if code in _KOKORO_LANG_CODES:
        return code
    return _KOKORO_LANG_ALIASES.get(code)


def _infer_kokoro_lang_code(voice: str) -> Optional[str]:
    """Infer Kokoro language code from a voice name prefix."""
    if not voice:
        return None
    code = voice.strip().lower()[:1]
    if code in _KOKORO_LANG_CODES:
        return code
    return None


def _is_auto_lang(lang_code: Optional[str]) -> bool:
    if not lang_code:
        return False
    return lang_code.strip().lower() in _AUTO_LANG_TOKENS


def _normalize_voice_map(voice_map: Optional[dict]) -> dict:
    if not isinstance(voice_map, dict):
        return {}
    normalized = {}
    for key, value in voice_map.items():
        code = _normalize_kokoro_lang_code(str(key))
        if code is None and isinstance(key, str):
            code = _infer_kokoro_lang_code(key)
        if code in _KOKORO_LANG_CODES and isinstance(value, str):
            normalized[code] = value
    return normalized


def _detect_kokoro_lang_code(text: str) -> str:
    if not text:
        return "a"
    if _CJK_RE.search(text):
        return "z"
    lowered = text.lower()
    if _FRENCH_CHARS_RE.search(lowered):
        return "f"
    tokens = re.findall(r"[a-zàâäçéèêëîïôöùûüÿœæ']+", lowered)
    if tokens:
        hits = sum(1 for t in tokens if t in _FRENCH_WORDS)
        if hits >= 2 or (hits > 0 and hits / len(tokens) > 0.25):
            return "f"
    return "a"


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def create_stt_model(realtime_cfg: dict) -> Any:
    """Create an STT model from *realtime_cfg*.

    Returns an object with ``.stt((sample_rate, np.ndarray)) -> str``.
    """
    stt_cfg = realtime_cfg.get("stt", {})
    backend = stt_cfg.get("backend", "fastrtc")

    if backend == "fastrtc":
        model_name = stt_cfg.get("fastrtc", {}).get("model", "moonshine/base")
        from fastrtc import get_stt_model
        return get_stt_model(model_name)

    if backend == "mlx":
        mlx_opts = stt_cfg.get("mlx", {})
        model_name = mlx_opts.get(
            "model", "mlx-community/whisper-base-mlx"
        )
        return MlxSttWrapper(model_name=model_name)

    raise ValueError(f"Unknown STT backend: {backend!r}")


def create_tts_model(realtime_cfg: dict) -> Any:
    """Create a TTS model from *realtime_cfg*.

    Returns an object with ``.stream_tts_sync(text) -> Generator``.
    """
    tts_cfg = realtime_cfg.get("tts", {})
    backend = tts_cfg.get("backend", "fastrtc")

    if backend == "fastrtc":
        model_name = tts_cfg.get("fastrtc", {}).get("model", "kokoro")
        from fastrtc import get_tts_model
        return get_tts_model(model_name)

    if backend == "mlx":
        mlx_opts = tts_cfg.get("mlx", {})
        model_name = mlx_opts.get(
            "model", "mlx-community/Kokoro-82M-bf16"
        )
        voice = mlx_opts.get("voice", "af_heart")
        lang_code = mlx_opts.get("lang_code")
        voice_map = mlx_opts.get("voice_map")
        speed = float(mlx_opts.get("speed", 1.0))
        return MlxTtsWrapper(
            model_name=model_name,
            voice=voice,
            speed=speed,
            lang_code=lang_code,
            voice_map=voice_map,
        )

    raise ValueError(f"Unknown TTS backend: {backend!r}")


# ---------------------------------------------------------------------------
# mlx-audio wrappers
# ---------------------------------------------------------------------------

class MlxSttWrapper:
    """Adapts mlx-audio Whisper to the ``.stt()`` interface.

    Calls ``model.generate(np.ndarray)`` directly — no temp files needed.
    """

    _TARGET_SR = 16_000

    def __init__(self, model_name: str) -> None:
        try:
            from mlx_audio.stt.utils import load_model
        except (ImportError, ModuleNotFoundError) as exc:
            raise ImportError(
                "mlx-audio STT API not available. "
                "Install with `pip install -e '.[realtime-mlx]'`."
            ) from exc

        logger.info("Loading mlx-audio STT model: %s", model_name)
        self._model = load_model(model_name)
        self._model_name = model_name

    def stt(self, audio: Tuple[int, np.ndarray]) -> str:
        """Transcribe audio.

        Args:
            audio: ``(sample_rate, samples)`` where *samples* is a 1-D
                   int16/float32 numpy array.

        Returns:
            Transcribed text.
        """
        sample_rate, samples = audio

        # Convert int16 → float32 normalised to [-1, 1]
        if np.issubdtype(samples.dtype, np.integer):
            samples = samples.astype(np.float32) / 32768.0

        # Ensure mono
        if samples.ndim > 1:
            samples = samples.mean(axis=-1)

        # Resample to 16 kHz if needed
        if sample_rate != self._TARGET_SR:
            from mlx_audio.stt.utils import resample_audio
            samples = resample_audio(samples, sample_rate, self._TARGET_SR)

        result = self._model.generate(samples, verbose=None)
        return result.text or ""


class MlxTtsWrapper:
    """Adapts mlx-audio Kokoro TTS to the ``.stream_tts_sync()`` interface.

    Yields ``(sample_rate, np.ndarray)`` tuples compatible with FastRTC's
    Kokoro TTS.
    """

    def __init__(
        self,
        model_name: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        lang_code: Optional[str] = None,
        voice_map: Optional[dict] = None,
    ) -> None:
        try:
            from mlx_audio.tts.utils import load_model as load_tts_model
        except (ImportError, ModuleNotFoundError) as exc:
            raise ImportError(
                "mlx-audio TTS API not available. "
                "Install with `pip install -e '.[realtime-mlx]'`."
            ) from exc

        logger.info("Loading mlx-audio TTS model: %s", model_name)
        self._model = load_tts_model(model_name)
        self._voice = voice
        self._speed = speed
        self._auto_lang = _is_auto_lang(lang_code)
        normalized = _normalize_kokoro_lang_code(lang_code)
        self._lang_code = normalized or _infer_kokoro_lang_code(voice) or "a"
        self._voice_map = _normalize_voice_map(voice_map)

    def stream_tts_sync(
        self, text: str
    ) -> Generator[Tuple[int, np.ndarray], None, None]:
        """Synthesise *text* and yield ``(sample_rate, np.ndarray)`` chunks.

        The audio is converted from the model's native ``mx.array`` float32
        to int16 PCM, matching the FastRTC TTS contract.
        """
        if self._auto_lang:
            lang_code = _detect_kokoro_lang_code(text)
            voice = (
                self._voice_map.get(lang_code)
                or _DEFAULT_VOICE_MAP.get(lang_code)
                or self._voice
            )
        else:
            lang_code = self._lang_code
            voice = self._voice

        for result in self._model.generate(
            text=text,
            voice=voice,
            speed=self._speed,
            lang_code=lang_code,
        ):
            audio_mx = result.audio          # mx.array, float32
            sr = int(result.sample_rate)
            audio_np = np.array(audio_mx, dtype=np.float32)
            audio_int16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)
            yield (sr, audio_int16)
