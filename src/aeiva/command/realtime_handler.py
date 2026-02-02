"""
RealtimePipelineHandler: Bridges FastRTC WebRTC streaming with the Aeiva Agent EventBus.

Data flow (audio):
    User speaks -> FastRTC WebRTC -> ReplyOnPause (VAD) -> STT (local)
        -> text -> emit('perception.realtime') -> Agent pipeline
        -> response text -> response_queue -> TTS (local)
        -> audio chunks -> WebRTC -> speaker

Data flow (text):
    User types text -> WebRTC textbox -> handler -> emit('perception.realtime')
        -> Agent pipeline -> response text -> response_queue -> chatbot display

Data flow (multimodal):
    User speaks/types + camera frame -> handler -> base64-encode image
        -> emit('perception.realtime', payload={"text": ..., "images": [...]})
        -> Agent pipeline (litellm multimodal) -> response text -> TTS + chatbot
"""

import asyncio
import base64
import io
import logging
import queue
from typing import Any, Generator, Optional, Union

from aeiva.neuron import Signal

logger = logging.getLogger(__name__)


def encode_image_to_base64(image_array) -> Optional[str]:
    """Encode a numpy image array to a base64 JPEG string.

    Args:
        image_array: numpy array (H, W, 3) in uint8 RGB format

    Returns:
        Base64-encoded JPEG string, or None on failure
    """
    if image_array is None:
        return None
    try:
        from PIL import Image
        import numpy as np
        if hasattr(image_array, 'shape'):
            if isinstance(image_array, np.ndarray) and image_array.dtype != np.uint8:
                if np.issubdtype(image_array.dtype, np.floating):
                    image_array = (np.clip(image_array, 0.0, 1.0) * 255.0).astype(np.uint8)
                else:
                    image_array = image_array.astype(np.uint8)
            img = Image.fromarray(image_array)
        elif isinstance(image_array, Image.Image):
            img = image_array
        else:
            return None
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode image: {e}")
        return None


class RealtimePipelineHandler:
    """STT -> Agent EventBus -> TTS pipeline handler for FastRTC.

    This handler is called by FastRTC's ReplyOnPause when the user stops speaking
    (or sends text). It:
    1. Transcribes audio via STT (or uses textbox input directly)
    2. Optionally captures a camera frame and encodes it
    3. Emits a 'perception.realtime' event to the Agent
    4. Collects the Agent's response from response_queue
    5. Synthesizes audio via TTS and yields chunks back to WebRTC
    """

    def __init__(
        self,
        agent: Any,
        gateway: Any,
        response_queue: queue.Queue,
        stt_model: Any,
        tts_model: Any,
        config_dict: dict,
        route_token: Optional[str] = None,
    ):
        self.agent = agent
        self.gateway = gateway
        self.response_queue = response_queue
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.config_dict = config_dict
        self.route_token = route_token
        self.latest_camera_frame: Any = None

    def update_latest_frame(self, frame: Any) -> None:
        """Cache the latest webcam frame for fallback image sends."""
        if frame is not None:
            self.latest_camera_frame = frame

    def __call__(
        self,
        data: Any,
        chatbot: Optional[list] = None,
        camera_image: Any = None,
        uploaded_image: Any = None,
        files: Any = None,
        *extra: Any,
    ) -> Generator:
        """Called by ReplyOnPause. Accepts audio data or WebRTCData (audio + textbox).

        Args:
            data: Audio tuple (sample_rate, np.ndarray) or WebRTCData
            chatbot: Current chatbot history (list of message dicts)
            camera_image: Optional camera frame (numpy array) for multimodal input
            uploaded_image: Optional uploaded image (numpy array) for multimodal input

        Yields:
            Audio chunks (sample_rate, np.ndarray) for TTS playback,
            plus AdditionalOutputs for chatbot updates.
        """
        from fastrtc import AdditionalOutputs

        chatbot = chatbot if chatbot is not None else []

        # 1. Extract user text: from audio (STT) or from textbox
        text = self._extract_text(data)
        if not text or not text.strip():
            return

        # 2. Update chatbot with user message
        chatbot = list(chatbot)
        chatbot.append({"role": "user", "content": text})
        yield AdditionalOutputs(chatbot)

        # 3. Build payload (text-only or multimodal)
        payload = self._build_payload(text, camera_image, uploaded_image)

        # 4. Emit to Agent EventBus (through gateway)
        try:
            if self.gateway is not None:
                signal = self.gateway.build_input_signal(
                    payload,
                    source="perception.realtime",
                    route=self.route_token,
                )
            else:
                signal = Signal(source="perception.realtime", data=payload)
            if self.gateway is None:
                asyncio.run_coroutine_threadsafe(
                    self.agent.event_bus.emit('perception.realtime', payload=payload),
                    self.agent.event_bus.loop
                ).result(timeout=5)
            else:
                asyncio.run_coroutine_threadsafe(
                    self.gateway.emit_input(
                        signal,
                        route=self.route_token,
                        add_pending_route=True,
                        event_name="perception.stimuli",
                    ),
                    self.agent.event_bus.loop
                ).result(timeout=5)
        except Exception as e:
            logger.error(f"Failed to emit perception.realtime: {e}")
            chatbot.append({"role": "assistant", "content": f"Error: {e}"})
            yield AdditionalOutputs(chatbot)
            return

        stream = self.config_dict.get("llm_gateway_config", {}).get("llm_stream", False)

        # 5. Collect response from Agent (streaming or non-streaming)
        if stream:
            chatbot.append({"role": "assistant", "content": ""})
            response_text = yield from self._collect_response_stream(chatbot)
        else:
            response_text = self._collect_response()
            chatbot.append({"role": "assistant", "content": response_text})
            yield AdditionalOutputs(chatbot)

        # 6. TTS -> yield audio chunks (after full text available)
        if self.tts_model is not None and response_text:
            try:
                for chunk in self.tts_model.stream_tts_sync(response_text):
                    yield chunk
            except Exception as e:
                logger.error(f"TTS error: {e}")

    def _build_payload(
        self,
        text: str,
        camera_image: Any = None,
        uploaded_image: Any = None,
    ) -> Union[str, dict]:
        """Build event payload, including image if available.

        Args:
            text: User text message
            camera_image: Optional numpy image array from webcam
            uploaded_image: Optional numpy image array from uploads

        Returns:
            Plain text string or dict with text + base64 images
        """
        chosen_image = uploaded_image if uploaded_image is not None else camera_image
        if chosen_image is None:
            chosen_image = self.latest_camera_frame
        if chosen_image is None:
            return text

        img_b64 = encode_image_to_base64(chosen_image)
        if img_b64 is None:
            return text

        return {"text": text, "images": [img_b64]}

    def _extract_text(self, data: Any) -> str:
        """Extract text from audio (via STT) or from textbox input.

        Args:
            data: Audio tuple, WebRTCData, or string

        Returns:
            Transcribed or typed text
        """
        try:
            from fastrtc import WebRTCData
            if isinstance(data, WebRTCData):
                if data.audio is not None and data.audio[1].size > 0:
                    return self.stt_model.stt(data.audio)
                return data.textbox or ""
        except ImportError:
            pass

        if isinstance(data, tuple) and len(data) == 2:
            # Pure audio tuple (sample_rate, np.ndarray)
            if self.stt_model is not None:
                return self.stt_model.stt(data)
            return ""

        return str(data) if data else ""

    def _collect_response(self, timeout: float = 30.0) -> str:
        """Collect streaming or non-streaming response from the Agent.

        Reads from response_queue until <END_OF_RESPONSE> marker (streaming)
        or a single message (non-streaming).

        Args:
            timeout: Maximum seconds to wait for response

        Returns:
            Complete response text
        """
        stream = self.config_dict.get("llm_gateway_config", {}).get("llm_stream", False)
        response_parts = []

        if stream:
            while True:
                try:
                    chunk = self.response_queue.get(timeout=timeout)
                    if chunk == "<END_OF_RESPONSE>":
                        break
                    response_parts.append(str(chunk))
                except queue.Empty:
                    logger.warning("Timeout waiting for streaming response chunk")
                    break
        else:
            try:
                response = self.response_queue.get(timeout=timeout)
                response_parts.append(str(response))
            except queue.Empty:
                logger.warning("Timeout waiting for response")
                response_parts.append("I'm sorry, I didn't receive a response in time.")

        return "".join(response_parts)

    def _collect_response_stream(self, chatbot: list, timeout: float = 30.0) -> str:
        """Stream response chunks to the chatbot as they arrive.

        Args:
            chatbot: Current chatbot history (list of message dicts)
            timeout: Maximum seconds to wait for response chunks

        Returns:
            Complete response text
        """
        from fastrtc import AdditionalOutputs
        response_parts = []

        while True:
            try:
                chunk = self.response_queue.get(timeout=timeout)
            except queue.Empty:
                logger.warning("Timeout waiting for streaming response chunk")
                break

            if chunk == "<END_OF_RESPONSE>":
                break

            response_parts.append(str(chunk))
            chatbot[-1]["content"] = "".join(response_parts)
            yield AdditionalOutputs(chatbot)

        return "".join(response_parts)
