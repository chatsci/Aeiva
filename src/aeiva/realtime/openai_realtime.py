"""
OpenAI Realtime (WebSocket) client + Gradio WebRTC handler.

Provides true realtime audio streaming (and optional video frames) over
OpenAI's Realtime API. This module is used by aeiva_chat_realtime when
realtime_config.mode == "live" and provider == "openai".
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, ClassVar, Optional

import numpy as np

try:
    from gradio_webrtc import AsyncAudioVideoStreamHandler, AdditionalOutputs
except ImportError:  # pragma: no cover - optional dependency
    AsyncAudioVideoStreamHandler = object  # type: ignore
    AdditionalOutputs = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class OpenAIRealtimeConfig:
    api_key: str
    model: str = "gpt-realtime"
    base_url: str = "wss://api.openai.com/v1/realtime"
    instructions: Optional[str] = None
    voice: str = "alloy"
    input_audio_format: str = "pcm16"
    output_audio_format: str = "pcm16"
    turn_detection: bool = True
    send_video: bool = False
    video_fps: float = 1.0


class OpenAIRealtimeClient:
    """Low-level WebSocket client for OpenAI Realtime API."""

    def __init__(
        self,
        config: OpenAIRealtimeConfig,
        audio_queue: asyncio.Queue,
        text_queue: asyncio.Queue,
    ):
        self.config = config
        self.audio_queue = audio_queue
        self.text_queue = text_queue
        self._ws = None
        self._connected = asyncio.Event()
        self._recv_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        if self._connected.is_set():
            return
        try:
            import websockets
        except ImportError as e:
            raise RuntimeError(
                "websockets is required for OpenAI realtime. "
                "Install with: pip install -e '.[realtime]'"
            ) from e

        url = f"{self.config.base_url}?model={self.config.model}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "OpenAI-Beta": "realtime=v1",
        }
        self._ws = await websockets.connect(url, extra_headers=headers)
        await self._send_session_update()
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._connected.set()

    async def close(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws is not None:
            await self._ws.close()
        self._connected.clear()

    async def send_event(self, event: dict) -> None:
        if not self._connected.is_set():
            await self.connect()
        if self._ws is None:
            return
        await self._ws.send(json.dumps(event))

    async def send_audio(self, audio_array: np.ndarray) -> None:
        if audio_array.size == 0:
            return
        if audio_array.dtype != np.int16:
            if np.issubdtype(audio_array.dtype, np.floating):
                audio_array = (np.clip(audio_array, -1.0, 1.0) * 32767.0).astype(np.int16)
            else:
                audio_array = audio_array.astype(np.int16)

        audio_b64 = base64.b64encode(audio_array.tobytes()).decode("utf-8")
        await self.send_event({
            "type": "input_audio_buffer.append",
            "audio": audio_b64,
        })

    async def send_text(self, text: str) -> None:
        if not text:
            return
        await self.send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": text},
                ],
            },
        })
        await self.send_event({"type": "response.create"})

    async def send_image(self, image_b64: str) -> None:
        if not image_b64:
            return
        await self.send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{image_b64}",
                    }
                ],
            },
        })

    async def _send_session_update(self) -> None:
        session = {
            "modalities": ["text", "audio"],
            "input_audio_format": self.config.input_audio_format,
            "output_audio_format": self.config.output_audio_format,
            "voice": self.config.voice,
        }
        if self.config.instructions:
            session["instructions"] = self.config.instructions
        if self.config.turn_detection:
            session["turn_detection"] = {"type": "server_vad"}

        await self.send_event({
            "type": "session.update",
            "session": session,
        })

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for msg in self._ws:
                try:
                    data = json.loads(msg)
                except Exception:
                    continue
                event_type = data.get("type", "")

                if event_type == "response.audio.delta":
                    audio_b64 = data.get("delta") or data.get("audio")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                        self.audio_queue.put_nowait(audio_array)

                elif event_type == "response.text.delta":
                    delta = data.get("delta", "")
                    if delta:
                        self.text_queue.put_nowait(delta)

                elif event_type == "response.audio_transcript.delta":
                    delta = data.get("delta", "")
                    if delta:
                        self.text_queue.put_nowait(delta)

                elif event_type == "response.done":
                    self.text_queue.put_nowait("<END_OF_RESPONSE>")

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"OpenAI realtime recv loop error: {e}")


class OpenAIRealtimeHandler(AsyncAudioVideoStreamHandler):
    """Gradio WebRTC handler for OpenAI realtime audio+video."""

    _active_instance: ClassVar[Optional["OpenAIRealtimeHandler"]] = None

    def __init__(self, config: OpenAIRealtimeConfig):
        if AsyncAudioVideoStreamHandler is object:
            raise RuntimeError(
                "gradio-webrtc is required for live realtime mode. "
                "Install with: pip install -e '.[realtime]'"
            )
        self.config = config
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.text_queue: asyncio.Queue = asyncio.Queue()
        self.client = OpenAIRealtimeClient(config, self.audio_queue, self.text_queue)
        self.last_video_sent = 0.0
        self.chatbot = []
        self.assistant_active = False
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,
            output_frame_size=960,
            input_sample_rate=24000,
        )

    def copy(self) -> "OpenAIRealtimeHandler":
        cloned = OpenAIRealtimeHandler(self.config)
        OpenAIRealtimeHandler._active_instance = cloned
        return cloned

    @classmethod
    def get_active(cls) -> Optional["OpenAIRealtimeHandler"]:
        return cls._active_instance

    async def _ensure_connected(self) -> None:
        await self.client.connect()

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        await self._ensure_connected()
        _, array = frame
        array = np.squeeze(array)
        await self.client.send_audio(array)

    async def emit(self) -> Any:
        await self._ensure_connected()
        await self._sync_chatbot()

        text_updated = await self._drain_text_queue()
        try:
            audio = self.audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            audio = None

        if audio is not None:
            if text_updated:
                return (self.output_sample_rate, audio), AdditionalOutputs(self.chatbot)
            return (self.output_sample_rate, audio)

        if text_updated:
            return AdditionalOutputs(self.chatbot)

        return None

    async def video_receive(self, frame: np.ndarray) -> None:
        if not self.config.send_video:
            return
        now = time.time()
        if now - self.last_video_sent < 1.0 / max(self.config.video_fps, 0.1):
            return
        self.last_video_sent = now
        image_b64 = self._encode_image(frame)
        if image_b64:
            await self.client.send_image(image_b64)

    async def video_emit(self) -> Any:
        return None

    async def send_text(self, text: str) -> None:
        await self._ensure_connected()
        await self._sync_chatbot()
        await self.client.send_text(text)

    async def _sync_chatbot(self) -> None:
        if self.chatbot:
            return
        if not self.args_set.is_set():
            await self.wait_for_args()
        if self.latest_args and len(self.latest_args) > 1:
            self.chatbot = list(self.latest_args[1]) or []

    async def _drain_text_queue(self) -> bool:
        updated = False
        while True:
            try:
                chunk = self.text_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if chunk == "<END_OF_RESPONSE>":
                self.assistant_active = False
                continue
            if not self.assistant_active:
                self.chatbot.append({"role": "assistant", "content": ""})
                self.assistant_active = True
            self.chatbot[-1]["content"] += str(chunk)
            updated = True
        return updated

    @staticmethod
    def _encode_image(frame: np.ndarray) -> Optional[str]:
        try:
            from PIL import Image
            import io
            if frame.dtype != np.uint8:
                if np.issubdtype(frame.dtype, np.floating):
                    frame = (np.clip(frame, 0.0, 1.0) * 255.0).astype(np.uint8)
                else:
                    frame = frame.astype(np.uint8)
            img = Image.fromarray(frame)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to encode frame: {e}")
            return None
