import asyncio
import threading
import logging
from typing import Union, Optional, Tuple

import cv2
import numpy as np

from aeiva.perception.sensor.sensor import Sensor

logger = logging.getLogger(__name__)

class VideoStreamSensor(Sensor):
    """
    A sensor that captures video frames from camera/file and emits them via the EventBus.

    Parameters (via `params` dict):
    --------------------------------------------------------------------
    source_type: str
        'camera', 'file', or 'none'
    video_source: Union[int, str]
        If source_type='camera', an int index (e.g. 0 for default cam).
        If source_type='file', a file path (string).
        If source_type='none', no capturing is done.
    emit_event_name: str
        Defaults to 'perception.video_frame'
    fps: int
        Desired capture frames per second. We'll wait ~1/fps between frames (approx).
    resize: Optional[Tuple[int,int]]
        If not None, (width, height) to which frames are resized.
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
        Start capturing video in a background thread.
        """
        if self.source_type == "none":
            logger.warning(f"[{self.name}] source_type='none'. No video capturing.")
            return

        if not self.event_bus.loop:
            raise RuntimeError(f"[{self.name}] EventBus loop is not set. Cannot start video capture.")

        # Initialize the capture (camera/file)
        if self.source_type == "camera":
            self._capture = cv2.VideoCapture(int(self.video_source))
        elif self.source_type == "file":
            self._capture = cv2.VideoCapture(str(self.video_source))
        else:
            raise ValueError(f"[{self.name}] Unknown source_type: {self.source_type}")

        if not self._capture or not self._capture.isOpened():
            error_msg = f"[{self.name}] Unable to open video source={self.video_source}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Optionally set camera FPS if needed. Some cameras won't respect it fully.
        if self.source_type == "camera" and self.fps > 0:
            self._capture.set(cv2.CAP_PROP_FPS, float(self.fps))

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        logger.debug(f"[{self.name}] VideoStreamSensor started (source={self.video_source}).")

    def _capture_loop(self):
        """
        Background thread reading frames from cv2.VideoCapture and emitting them.
        """
        loop = self.event_bus.loop
        if not loop:
            logger.error(f"[{self.name}] No event bus loop found; cannot emit video frames.")
            return

        # The delay for each frame, to approximate desired fps
        frame_delay = 1.0 / float(self.fps) if self.fps > 0 else 0

        while self._running and self._capture and self._capture.isOpened():
            ret, frame = self._capture.read()
            if not ret:
                logger.debug(f"[{self.name}] Frame grab failed or end of file.")
                break

            # If resize is specified, resize the frame
            if self.resize is not None:
                (width, height) = self.resize
                frame = cv2.resize(frame, (width, height))

            # By default, frame is BGR. If you want to convert to RGB:
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # We'll keep BGR to keep it consistent with OpenCV usage:
            frame_data = np.ascontiguousarray(frame)

            # Emit the frame
            asyncio.run_coroutine_threadsafe(
                self.event_bus.emit(self.emit_event_name, payload=frame_data),
                loop
            )

            if frame_delay > 0:
                # Use OpenCV waitKey or time.sleep
                # time.sleep() is safer in a thread
                import time
                time.sleep(frame_delay)

        self._running = False
        logger.debug(f"[{self.name}] Exiting video capture loop.")

    async def stop(self):
        """
        Stop the sensor by ending the capture thread and releasing the source.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        if self._capture:
            self._capture.release()
            self._capture = None

        logger.debug(f"[{self.name}] VideoStreamSensor stopped.")