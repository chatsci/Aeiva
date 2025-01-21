import asyncio
import threading
import logging
from typing import Union, Optional

import cv2
import numpy as np

from aeiva.perception.sensor.sensor import Sensor

class VideoStreamSensor(Sensor):
    """
    A sensor that captures video frames from various sources and emits them via the EventBus.

    Parameters (passed via `params` dict):
    --------------------------------------------------------------------
    source_type: str
        Type of video source. Can be 'camera', 'file', or 'none' (dummy source).
    video_source: Union[int, str]
        - If source_type == 'camera', this can be an integer index (e.g., 0 for default camera).
        - If source_type == 'file', this can be a string path to a video file (e.g., 'video.mp4').
        - If source_type == 'none', no capturing is done.
    emit_event_name: str
        The event name to emit on the event_bus. Defaults to 'perception.video_frame'.
    fps: int
        Frames per second to capture from the source. Defaults to 30.
    resize: Optional[tuple[int, int]]
        If not None, resize frames to this (width, height).
    """

    def __init__(self, name: str, params: dict, event_bus):
        super().__init__(name, params, event_bus)
        self.source_type = params.get("source_type", "camera")
        self.video_source: Union[int, str] = params.get("video_source", 0)
        self.emit_event_name = params.get("emit_event_name", "perception.video_frame")
        self.fps = params.get("fps", 30)
        self.resize = params.get("resize", None)

        # Internal state
        self._running = False
        self._capture = None
        self._thread: Optional[threading.Thread] = None

    async def start(self):
        """
        Starts the sensor by initializing the capture source and spawning the capture thread.
        """
        if self.source_type == "none":
            logging.warning(f"[{self.name}] source_type is 'none'. No video capturing.")
            return

        # Open the camera or file source
        if self.source_type == "camera":
            self._capture = cv2.VideoCapture(self.video_source)
        elif self.source_type == "file":
            self._capture = cv2.VideoCapture(str(self.video_source))
        else:
            raise ValueError(f"[{self.name}] Unknown source_type: {self.source_type}")

        if self._capture and not self._capture.isOpened():
            raise RuntimeError(f"[{self.name}] Unable to open video source: {self.video_source}")

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        logging.debug(f"[{self.name}] VideoStreamSensor started (source={self.video_source}).")

    def _capture_loop(self):
        """
        The main loop running in a background thread that reads frames from the source
        and emits them to the EventBus.
        """
        loop = self.event_bus.loop
        if not loop:
            logging.error(f"[{self.name}] EventBus loop is not set. Cannot emit events.")
            return

        frame_delay = 1.0 / self.fps if self.fps > 0 else 0.033

        while self._running and self._capture and self._capture.isOpened():
            ret, frame = self._capture.read()
            if not ret:
                # Possibly end of file or camera disconnected
                logging.debug(f"[{self.name}] Failed to read frame.")
                break

            if self.resize is not None:
                width, height = self.resize
                frame = cv2.resize(frame, (width, height))

            # Create a copy or convert to desired color space if needed (e.g., BGR -> RGB)
            # For now, let's keep it as BGR (OpenCV default).
            frame_data = np.ascontiguousarray(frame)

            # Emit the frame to the event_bus
            asyncio.run_coroutine_threadsafe(
                self.event_bus.emit(self.emit_event_name, payload=frame_data),
                loop,
            )

            # Sleep to maintain approximate framerate
            if frame_delay > 0:
                cv2.waitKey(int(frame_delay * 1000))

        self._running = False
        logging.debug(f"[{self.name}] Exiting capture loop.")

    async def stop(self):
        """
        Stops the sensor by signaling the thread to stop and waiting for it to finish.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()
        if self._capture:
            self._capture.release()
        logging.debug(f"[{self.name}] VideoStreamSensor stopped.")