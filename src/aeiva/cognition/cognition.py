"""
Cognition: The central orchestrator neuron for cognitive processing.

This neuron coordinates thinking by wrapping the Brain abstraction.
The actual thinking is powered by Brain -> LLMClient -> litellm.

Architecture:
    Cognition
        └── Brain (abstract)
            └── LLMBrain (concrete)
                └── LLMClient
                    └── litellm -> OpenAI/Anthropic/etc.

Usage:
    from aeiva.cognition import Cognition
    from aeiva.cognition.brain.llm_brain import LLMBrain

    brain = LLMBrain({'llm_gateway_config': {...}})
    brain.setup()

    cognition = Cognition(name="cognition", brain=brain, event_bus=bus)
    await cognition.setup()

Event Flow:
    perception.output ─┬─> Cognition ─> cognition.thought
    cognition.think   ─┤
    cognition.query   ─┘
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import json

from aeiva.neuron import BaseNeuron, Signal, NeuronConfig
from aeiva.event.event_names import EventNames

if TYPE_CHECKING:
    from aeiva.cognition.brain.base_brain import Brain
    from aeiva.event.event_bus import EventBus

logger = logging.getLogger(__name__)


DEFAULT_INPUT_EVENTS = [
    EventNames.PERCEPTION_OUTPUT,
    EventNames.COGNITION_THINK,
    EventNames.COGNITION_QUERY,
]


@dataclass
class CognitionConfig(NeuronConfig):
    """Configuration for Cognition neuron."""
    input_events: List[str] = field(default_factory=lambda: DEFAULT_INPUT_EVENTS.copy())
    output_event: str = EventNames.COGNITION_THOUGHT
    max_history: int = 20


@dataclass
class CognitionState:
    """Current cognitive state."""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    last_thought: Optional[str] = None
    thinking: bool = False

    def add_turn(self, role: str, content: str) -> None:
        """Add a conversation turn."""
        self.conversation_history.append({"role": role, "content": content})

    def get_recent_history(self, n: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history."""
        return self.conversation_history[-n:]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conversation_history": self.conversation_history.copy(),
            "last_thought": self.last_thought,
            "thinking": self.thinking,
        }


class Cognition(BaseNeuron):
    """
    The cognition neuron - orchestrates thinking using Brain.

    Receives stimuli from perception or direct think requests,
    processes input through Brain (LLMBrain -> LLMClient -> litellm),
    and emits thoughts for downstream consumption.
    """

    EMISSIONS = [EventNames.COGNITION_THOUGHT, EventNames.COGNITION_QUERY_RESPONSE]
    CONFIG_CLASS = CognitionConfig

    def __init__(
        self,
        name: str = "cognition",
        config: Dict = None,
        event_bus: "EventBus" = None,
        brain: "Brain" = None,
        **kwargs
    ):
        neuron_config = self.build_config(config or {})
        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)

        self.SUBSCRIPTIONS = self.config.input_events.copy()
        self.state = CognitionState()
        self.brain = brain
        self.thoughts_produced = 0
        self.skipped = 0

    async def setup(self) -> None:
        """Initialize the cognition neuron."""
        await super().setup()
        logger.info(f"{self.name} setup complete, brain={'attached' if self.brain else 'none'}")

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """Process incoming signal and produce a thought."""
        source = signal.source

        if EventNames.COGNITION_QUERY in source:
            return await self.handle_query(signal)

        if source.startswith(EventNames.ALL_PERCEPTION[:-1]) or EventNames.COGNITION_THINK in source:
            return await self.handle_think(signal)

        self.skipped += 1
        return None

    async def send(self, output: Any, parent: Signal = None) -> None:
        """
        Send output to the configured cognition output event.

        This keeps non-streaming cognition aligned with the expected
        `cognition.thought` event.
        """
        if output is None:
            return

        if parent:
            signal = parent.child(self.name, output)
        else:
            signal = Signal(source=self.name, data=output)

        self.working.last_output = output

        if self.events:
            event_name = self.config.output_event or EventNames.COGNITION_THOUGHT
            emit_args = self.signal_to_event_args(event_name, signal)
            await self.events.emit(**emit_args)

    async def handle_think(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """Handle a think request - the core cognitive processing."""
        self.state.thinking = True

        try:
            input_content = self.extract_content(signal)
            if not input_content:
                return None
            if isinstance(input_content, list):
                text_parts = [b["text"] for b in input_content if b.get("type") == "text"]
                history_content = " ".join(text_parts) or "[multimodal input]"
            else:
                history_content = input_content
            meta = self.extract_metadata(signal)
            stream = False
            use_async = False
            if hasattr(self.brain, "config") and self.brain.config:
                stream = getattr(self.brain.config, "llm_stream", False)
                use_async = getattr(self.brain.config, "llm_use_async", False)
            if isinstance(meta, dict):
                if "llm_stream" in meta:
                    stream = bool(meta["llm_stream"])
                if "llm_use_async" in meta:
                    use_async = bool(meta["llm_use_async"])

            origin_trace_id = signal.parent_id or signal.trace_id
            if stream and self.brain is not None:
                thought = await self._think_streaming(
                    input_content,
                    signal.source,
                    use_async,
                    history_content,
                    origin_trace_id,
                    meta,
                )
            else:
                thought = await self.think(input_content)

            # Store text-only version in history (avoid bloating with base64 images)
            self.state.add_turn("user", history_content)
            self.state.add_turn("assistant", thought)
            self.state.last_thought = thought

            max_turns = self.config.max_history * 2
            if len(self.state.conversation_history) > max_turns:
                excess = len(self.state.conversation_history) - max_turns
                self.state.conversation_history = self.state.conversation_history[excess:]

            self.thoughts_produced += 1

            if stream:
                return None

            return {
                "thought": thought,
                "full_thought": thought,
                "input": history_content,
                "source": signal.source,
                "origin_trace_id": origin_trace_id,
                "meta": meta,
                "history_length": len(self.state.conversation_history),
                "streaming": False,
                "final": True,
            }

        finally:
            self.state.thinking = False

    async def _think_streaming(
        self,
        input_content: Union[str, list],
        source: str,
        use_async: bool,
        user_input: Optional[str],
        origin_trace_id: Optional[str],
        meta: Optional[dict],
    ) -> str:
        """Stream thought chunks as cognition.thought events."""
        response_parts = []
        if self.brain is None:
            return ""

        messages = [{"role": "user", "content": input_content}]
        async for chunk in self.brain.think(messages, stream=True, use_async=use_async):
            if not isinstance(chunk, str):
                continue
            response_parts.append(chunk)
            await self._emit_thought_chunk(
                chunk,
                source,
                final=False,
                full_thought=None,
                user_input=None,
                origin_trace_id=origin_trace_id,
                meta=meta,
            )

        full_thought = "".join(response_parts)
        await self._emit_thought_chunk(
            "",
            source,
            final=True,
            full_thought=full_thought,
            user_input=user_input,
            origin_trace_id=origin_trace_id,
            meta=meta,
        )
        return full_thought

    async def _emit_thought_chunk(
        self,
        chunk: str,
        source: str,
        final: bool,
        full_thought: Optional[str],
        user_input: Optional[str],
        origin_trace_id: Optional[str] = None,
        meta: Optional[dict] = None,
    ) -> None:
        if not self.events:
            return
        payload = {
            "thought": chunk,
            "source": source,
            "streaming": True,
            "final": final,
            "full_thought": full_thought,
        }
        if user_input is not None:
            payload["input"] = user_input
        if origin_trace_id is not None:
            payload["origin_trace_id"] = origin_trace_id
        if isinstance(meta, dict) and meta:
            payload["meta"] = meta
        await self.events.emit(
            EventNames.COGNITION_THOUGHT,
            payload=payload,
        )

    def extract_content(self, signal: Signal) -> Optional[Union[str, list]]:
        """Extract content from a signal.

        Returns either a plain string (text-only) or a list of litellm content
        blocks for multimodal input (text + images).
        """
        data = signal.data

        if isinstance(data, str):
            return data

        if isinstance(data, dict):
            # Multimodal payload: {"text": "...", "images": ["base64..."]}
            if "images" in data and data["images"]:
                return self._build_multimodal_content(
                    data.get("text", ""), data["images"]
                )
            for key in ["content", "text", "message", "data", "input", "query"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, str):
                        return val
                    elif isinstance(val, dict) and "content" in val:
                        return str(val["content"])

        if hasattr(data, "signals") and data.signals:
            first_signal = data.signals[0]
            if hasattr(first_signal, "data"):
                inner = first_signal.data
                if isinstance(inner, dict):
                    if "images" in inner and inner["images"]:
                        return self._build_multimodal_content(
                            inner.get("text", ""), inner["images"]
                        )
                    for key in ["content", "text", "message", "data", "input", "query"]:
                        if key in inner and isinstance(inner[key], str):
                            return inner[key]
                return str(inner)

        if hasattr(data, "content"):
            return str(data.content)

        if data:
            return str(data)

        return None

    def extract_metadata(self, signal: Signal) -> Optional[dict]:
        """Extract metadata from a signal payload if present."""
        data = signal.data
        if isinstance(data, dict):
            meta = data.get("meta") or data.get("metadata")
            if isinstance(meta, dict):
                return meta
        if hasattr(data, "metadata") and isinstance(data.metadata, dict):
            return data.metadata
        if hasattr(data, "signals") and data.signals:
            for item in data.signals:
                meta = getattr(item, "metadata", None)
                if isinstance(meta, dict) and meta:
                    return meta
        return None

    @staticmethod
    def _build_multimodal_content(text: str, images: list) -> list:
        """Build litellm-format multimodal content blocks.

        Args:
            text: User text message
            images: List of base64-encoded image strings

        Returns:
            List of content blocks for litellm message format
        """
        blocks = []
        if text:
            blocks.append({"type": "text", "text": text})
        for img_b64 in images:
            if img_b64.startswith("data:"):
                url = img_b64
            else:
                url = f"data:image/jpeg;base64,{img_b64}"
            blocks.append({
                "type": "image_url",
                "image_url": {"url": url},
            })
        return blocks

    async def think(self, input_content: Union[str, list]) -> str:
        """Produce a thought using the Brain.

        Args:
            input_content: Plain text string or a list of litellm content
                blocks (for multimodal input with images).
        """
        if self.brain is not None:
            try:
                stream = False
                use_async = False
                if hasattr(self.brain, "config") and self.brain.config:
                    stream = getattr(self.brain.config, "llm_stream", False)
                    use_async = getattr(self.brain.config, "llm_use_async", False)

                messages = [{"role": "user", "content": input_content}]
                response_parts = []
                async for chunk in self.brain.think(messages, stream=stream, use_async=use_async):
                    if isinstance(chunk, str):
                        response_parts.append(chunk)
                return "".join(response_parts) if response_parts else ""
            except Exception as e:
                logger.warning(f"Brain error: {e}, returning placeholder")

        preview = input_content if isinstance(input_content, str) else "[multimodal]"
        return f"[Cognition] Received: {preview[:100]}..."

    async def handle_query(self, signal: Signal) -> Dict[str, Any]:
        """Handle cognitive state query requests."""
        data = signal.data if isinstance(signal.data, dict) else {}
        query_type = data.get("type", "state")

        if query_type == "state":
            return {
                "type": "state",
                "thinking": self.state.thinking,
                "last_thought": self.state.last_thought,
                "history_length": len(self.state.conversation_history),
                "has_brain": self.brain is not None,
            }

        elif query_type == "history":
            n = data.get("n", 10)
            return {
                "type": "history",
                "history": self.state.get_recent_history(n),
            }

        elif query_type == "clear":
            self.state.clear_history()
            self.state.last_thought = None
            return {
                "type": "clear",
                "status": "cleared",
            }

        else:
            return {
                "type": "error",
                "message": f"Unknown query type: {query_type}",
            }

    async def send(self, output: Any, parent: Signal = None) -> None:
        """Send cognition event."""
        if output is None:
            return

        signal = parent.child(self.name, output) if parent else Signal(source=self.name, data=output)
        self.working.last_output = output

        if self.events:
            emit_args = self.signal_to_event_args(self.config.output_event, signal)
            await self.events.emit(**emit_args)

    def health_check(self) -> dict:
        """Return health status."""
        health = super().health_check()
        health["thinking"] = self.state.thinking
        health["history_length"] = len(self.state.conversation_history)
        health["thoughts_produced"] = self.thoughts_produced
        health["has_brain"] = self.brain is not None
        return health

    def serialize(self) -> str:
        """Serialize state."""
        return json.dumps(self.state.to_dict())

    def deserialize(self, data: str) -> None:
        """Deserialize state."""
        parsed = json.loads(data)
        self.state = CognitionState(
            conversation_history=parsed.get("conversation_history", []),
            last_thought=parsed.get("last_thought"),
            thinking=False,
        )
