import asyncio
import threading
import logging
from typing import Optional, Union
import numpy as np
import pyaudio

from aeiva.perception.sensor.sensor import Sensor

class AudioStreamSensor(Sensor):
    """
    A sensor that captures audio samples from various sources and emits them via the EventBus.

    Parameters (passed via `params` dict):
    --------------------------------------------------------------------
    source_type: str
        Type of audio source. Can be 'microphone', 'file', or 'none' (dummy source).
        Currently, only 'microphone' is implemented in this example.
    device_index: Optional[int]
        Device index for the PyAudio input device, if using a microphone. Defaults to None.
    sample_rate: int
        Sample rate in Hz. Defaults to 16000.
    channels: int
        Number of audio channels. Defaults to 1.
    chunk_size: int
        Number of frames per buffer. Defaults to 1024.
    emit_event_name: str
        The event name to emit on the event_bus. Defaults to 'perception.audio_chunk'.
    """

    def __init__(self, name: str, params: dict, event_bus):
        super().__init__(name, params, event_bus)
        self.source_type = params.get("source_type", "microphone")
        self.device_index: Optional[int] = params.get("device_index", None)
        self.sample_rate = params.get("sample_rate", 16000)
        self.channels = params.get("channels", 1)
        self.chunk_size = params.get("chunk_size", 1024)
        self.emit_event_name = params.get("emit_event_name", "perception.audio_chunk")

        # Internal state
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._pyaudio_instance = pyaudio.PyAudio()
        self._stream = None

    async def start(self):
        """
        Starts capturing from the audio source in a background thread.
        """
        if self.source_type == "none":
            logging.warning(f"[{self.name}] source_type is 'none'. No audio capturing.")
            return

        if self.source_type != "microphone":
            raise NotImplementedError(f"[{self.name}] Only 'microphone' source_type is implemented.")

        # Open the microphone (or other audio input device)
        self._stream = self._pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index
        )

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        logging.debug(f"[{self.name}] AudioStreamSensor started (device_index={self.device_index}).")

    def _capture_loop(self):
        """
        Continuously capture audio chunks from the source and emit them to the EventBus.
        """
        loop = self.event_bus.loop
        if not loop:
            logging.error(f"[{self.name}] EventBus loop is not set. Cannot emit events.")
            return

        while self._running and self._stream and not self._stream.is_stopped():
            data = self._stream.read(self.chunk_size, exception_on_overflow=False)
            # Convert raw bytes to int16 numpy array
            audio_array = np.frombuffer(data, dtype=np.int16)

            # Emit the (sample_rate, audio_array) tuple
            asyncio.run_coroutine_threadsafe(
                self.event_bus.emit(self.emit_event_name, payload=(self.sample_rate, audio_array)),
                loop,
            )

        self._running = False
        logging.debug(f"[{self.name}] Exiting capture loop.")

    async def stop(self):
        """
        Stops the audio capturing thread and closes the audio stream.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        self._pyaudio_instance.terminate()
        logging.debug(f"[{self.name}] AudioStreamSensor stopped.")