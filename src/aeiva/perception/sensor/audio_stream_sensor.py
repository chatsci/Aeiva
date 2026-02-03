import asyncio
import threading
import logging
from typing import Optional

import numpy as np
import pyaudio

from aeiva.perception.sensor.sensor import Sensor
from aeiva.event.event_names import EventNames

logger = logging.getLogger(__name__)

class AudioStreamSensor(Sensor):
    """
    A sensor that captures audio samples (int16) from a 'microphone' source
    and emits them via the EventBus.

    Parameters (via `params` dict):
    --------------------------------------------------------------------
    source_type: str
        Type of audio source. Current valid value: 'microphone'
    device_index: Optional[int]
        PyAudio device index for input. If None, default device is used.
    sample_rate: int
        Audio sample rate in Hz. Defaults to 16000.
    channels: int
        Number of channels. Defaults to 1 (mono).
    chunk_size: int
        Frames per buffer (default=1024).
    emit_event_name: str
        The event name to emit with (sample_rate, audio_array) payload.
        Defaults to 'perception.audio_chunk'.
    """

    def __init__(self, name: str, params: dict, event_bus):
        super().__init__(name, params, event_bus)
        self.source_type = params.get("source_type", "microphone")
        self.device_index: Optional[int] = params.get("device_index", None)
        self.sample_rate = params.get("sample_rate", 16000)
        self.channels = params.get("channels", 1)
        self.chunk_size = params.get("chunk_size", 1024)
        self.emit_event_name = params.get("emit_event_name", EventNames.PERCEPTION_AUDIO_CHUNK)

        # Internal state
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._pyaudio_instance = None
        self._stream = None

    async def start(self):
        """
        Start capturing audio in a background thread.
        If 'source_type' is 'none', do nothing.
        """
        if self.source_type == "none":
            logger.warning(f"[{self.name}] source_type is 'none'. No audio capturing.")
            return

        if self.source_type != "microphone":
            raise NotImplementedError(f"[{self.name}] Unsupported source_type: {self.source_type}")

        # Ensure event_bus.loop is valid
        if not self.event_bus.loop:
            raise RuntimeError(f"[{self.name}] EventBus loop is not set. Cannot start audio capture.")

        # Initialize PyAudio
        self._pyaudio_instance = pyaudio.PyAudio()

        # Open the input stream
        try:
            self._stream = self._pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.device_index
            )
        except Exception as e:
            logger.error(f"[{self.name}] Failed to open audio stream: {e}")
            raise

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        logger.debug(f"[{self.name}] AudioStreamSensor started (device_index={self.device_index}).")

    def _capture_loop(self):
        """
        Continuously read audio chunks from PyAudio and emit them to the EventBus.
        """
        loop = self.event_bus.loop
        if not loop:
            logger.error(f"[{self.name}] No event bus loop found; cannot emit events.")
            return

        while self._running and self._stream and not self._stream.is_stopped():
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
            except Exception as e:
                logger.error(f"[{self.name}] Error reading audio stream: {e}")
                break

            # Convert raw bytes to int16 numpy array
            audio_array = np.frombuffer(data, dtype=np.int16)

            # Emit the (sample_rate, audio_array) tuple
            asyncio.run_coroutine_threadsafe(
                self.event_bus.emit(self.emit_event_name, payload=(self.sample_rate, audio_array)),
                loop
            )

        # Cleanup state if we exit the loop
        self._running = False
        logger.debug(f"[{self.name}] Exiting audio capture loop.")

    async def stop(self):
        """
        Stop the capturing thread and close the audio stream.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        if self._stream:
            if not self._stream.is_stopped():
                self._stream.stop_stream()
            self._stream.close()

        if self._pyaudio_instance:
            self._pyaudio_instance.terminate()
            self._pyaudio_instance = None

        logger.debug(f"[{self.name}] AudioStreamSensor stopped.")
