# test.py

import asyncio
import logging
import sys
import os

# If needed, adjust path so Python can import your modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aeiva.perception.sensor.audio_stream_sensor import AudioStreamSensor
from aeiva.perception.sensor.video_stream_sensor import VideoStreamSensor

# Mock event bus that just collects/prints events
class MockEventBus:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def emit(self, event_name: str, payload):
        print(f"[EventBus] Emitted event '{event_name}' with payload type: {type(payload)}")

async def main():
    logging.basicConfig(level=logging.DEBUG)

    event_bus = MockEventBus()

    # 1) Create the audio sensor
    audio_params = {
        "source_type": "microphone",  # or "none"
        "device_index": None,
        "sample_rate": 16000,
        "channels": 1,
        "chunk_size": 1024,
        "emit_event_name": "perception.audio_chunk"
    }
    audio_sensor = AudioStreamSensor(name="MicrophoneSensor", params=audio_params, event_bus=event_bus)

    # 2) Create the video sensor
    video_params = {
        "source_type": "camera",  # or "none"
        "video_source": 0,        # default camera
        "emit_event_name": "perception.video_frame",
        "fps": 10,                # lower FPS for demo
        "resize": None            # e.g. (320, 240) if you want smaller frames
    }
    video_sensor = VideoStreamSensor(name="CameraSensor", params=video_params, event_bus=event_bus)

    # Start sensors
    print("[TEST] Starting sensors...")
    await audio_sensor.start()
    await video_sensor.start()

    # Let them run ~10 seconds
    print("[TEST] Sensors running. Recording events for 10s...")
    await asyncio.sleep(10)

    # Stop sensors
    print("[TEST] Stopping sensors...")
    await audio_sensor.stop()
    await video_sensor.stop()

    print("[TEST] Done.")

if __name__ == "__main__":
    asyncio.run(main())