# test_sensors.py

import asyncio
import logging
from typing import Any, Callable, Dict
from aeiva.event.event_bus import EventBus, EventCancelled


async def main():
    logging.basicConfig(level=logging.DEBUG)
    
    event_bus = EventBus()
    event_bus.start()
    event_bus.loop = asyncio.get_running_loop()

    # Register event handlers
    @event_bus.on("perception.video_frame")
    async def handle_video_frame(event):
        # frame_data is a NumPy array (BGR)
        # We'll just log shape
        frame_data = event.payload
        print(f"[handle_video_frame] Received frame of shape: {frame_data.shape}")

    @event_bus.on("perception.audio_chunk")
    async def handle_audio_chunk(event):
        # payload is (sample_rate, numpy_array)
        sr, array = event.payload
        print(f"[handle_audio_chunk] Audio chunk: sr={sr}, shape={array.shape}")

    # Import the sensors
    from aeiva.perception.sensor.video_stream_sensor import VideoStreamSensor
    from aeiva.perception.sensor.audio_stream_sensor import AudioStreamSensor

    # Example 1: Video from local camera, index=0
    video_params = {
        "source_type": "camera",
        "video_source": 0,
        "emit_event_name": "perception.video_frame",
        "fps": 10,
        "resize": (320, 240),  # Optional
    }
    video_sensor = VideoStreamSensor("local_cam", video_params, event_bus)

    # Example 2: Audio from default microphone
    audio_params = {
        "source_type": "microphone",
        "device_index": None,  # or specify if needed
        "sample_rate": 16000,
        "channels": 1,
        "chunk_size": 1024,
        "emit_event_name": "perception.audio_chunk",
    }
    audio_sensor = AudioStreamSensor("mic_sensor", audio_params, event_bus)

    # Start the sensors
    await video_sensor.start()
    await audio_sensor.start()

    # Let them run for 10 seconds
    await asyncio.sleep(10)

    # Stop sensors
    await video_sensor.stop()
    await audio_sensor.stop()

if __name__ == "__main__":
    asyncio.run(main())