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
from aeiva.action.action_envelope import parse_action_envelope, resolve_action_mode

if TYPE_CHECKING:
    from aeiva.cognition.brain.base_brain import Brain
    from aeiva.event.event_bus import EventBus

logger = logging.getLogger(__name__)


DEFAULT_INPUT_EVENTS = [
    EventNames.PERCEPTION_OUTPUT,
    EventNames.COGNITION_THINK,
    EventNames.COGNITION_QUERY,
    EventNames.ACTION_RESULT,
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
    last_hint_trace_id: Optional[str] = None

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
            "last_hint_trace_id": self.last_hint_trace_id,
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
        self.config_dict = config or {}
        self.action_config = self.config_dict.get("action_config") or {}
        neuron_config = self.build_config(self.config_dict)
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

        if EventNames.ACTION_RESULT in source:
            return await self.handle_action_result(signal)

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
            actions = output.get("actions") if isinstance(output, dict) else None
            message_text = output.get("thought") if isinstance(output, dict) else None

            if message_text or not actions:
                event_name = self.config.output_event or EventNames.COGNITION_THOUGHT
                emit_args = self.signal_to_event_args(event_name, signal)
                await self.events.emit(**emit_args)

            if actions:
                action_context = output.get("action_context", {}) if isinstance(output, dict) else {}
                proposal = output.get("action_proposal", {}) if isinstance(output, dict) else {}
                await self._emit_action_plan(
                    actions,
                    action_context=action_context,
                    proposal=proposal,
                )

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
            action_mode = resolve_action_mode(self.action_config)
            force_json = action_mode == "json" or bool(self.action_config.get("force_json", False))
            if force_json and not self.action_config.get("stream_json", False):
                stream = False

            origin_trace_id = signal.parent_id or signal.trace_id
            if stream and self.brain is not None:
                thought = await self._think_streaming(
                    input_content,
                    signal.source,
                    use_async,
                    history_content,
                    origin_trace_id,
                    meta,
                    suppress_json_stream=action_mode != "off",
                )
            else:
                thought = await self.think(
                    input_content,
                    stream=stream,
                    use_async=use_async,
                )

            envelope, parse_errors = parse_action_envelope(thought)
            message_text = envelope.get("message") or ""
            actions = envelope.get("actions") or []

            action_context = self._build_action_context(
                origin_trace_id=origin_trace_id,
                user_input=history_content,
                meta=meta,
                action_hops=0,
            )
            actions = self._limit_actions(actions, action_context, parse_errors)

            if actions and not message_text and not stream:
                await self._emit_hint(
                    self.action_config.get("hint_text") or "Thinking...",
                    signal.source,
                    origin_trace_id=origin_trace_id,
                    meta=meta,
                )

            # Store text-only version in history (avoid bloating with base64 images)
            self.state.add_turn("user", history_content)
            self.state.add_turn("assistant", message_text or thought)
            self.state.last_thought = message_text or thought

            max_turns = self.config.max_history * 2
            if len(self.state.conversation_history) > max_turns:
                excess = len(self.state.conversation_history) - max_turns
                self.state.conversation_history = self.state.conversation_history[excess:]

            self.thoughts_produced += 1

            if stream:
                return None

            return {
                "thought": message_text,
                "full_thought": message_text,
                "raw_output": thought,
                "action_proposal": envelope,
                "actions": actions,
                "action_context": action_context,
                "input": history_content,
                "source": signal.source,
                "origin_trace_id": origin_trace_id,
                "meta": meta,
                "history_length": len(self.state.conversation_history),
                "streaming": False,
                "final": True,
                "parse_errors": parse_errors,
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
        *,
        suppress_json_stream: bool,
    ) -> str:
        """Stream thought chunks as cognition.thought events."""
        response_parts = []
        stream_allowed: Optional[bool] = None
        buffer: List[str] = []
        if self.brain is None:
            return ""

        messages = [{"role": "user", "content": input_content}]
        try:
            async for chunk in self.brain.think(messages, stream=True, use_async=use_async):
                if not isinstance(chunk, str):
                    continue
                response_parts.append(chunk)
                if not suppress_json_stream:
                    await self._emit_thought_chunk(
                        chunk,
                        source,
                        final=False,
                        full_thought=None,
                        user_input=None,
                        origin_trace_id=origin_trace_id,
                        meta=meta,
                    )
                    continue

                if stream_allowed is False:
                    continue

                buffer.append(chunk)
                preview = "".join(buffer)
                stripped = preview.lstrip()
                if not stripped:
                    continue

                if stripped.startswith("{"):
                    stream_allowed = False
                    buffer.clear()
                    continue

                stream_allowed = True
                await self._emit_thought_chunk(
                    preview,
                    source,
                    final=False,
                    full_thought=None,
                    user_input=None,
                    origin_trace_id=origin_trace_id,
                    meta=meta,
                )
                buffer.clear()
        except Exception as exc:
            logger.warning("Streaming failed, falling back to non-stream: %s", exc)
            return await self.think(
                input_content,
                stream=False,
                use_async=use_async,
            )

        full_thought = "".join(response_parts)
        envelope, parse_errors = parse_action_envelope(full_thought)
        message_text = envelope.get("message") or ""
        actions = envelope.get("actions") or []
        action_context = self._build_action_context(
            origin_trace_id=origin_trace_id,
            user_input=user_input,
            meta=meta,
            action_hops=0,
        )
        actions = self._limit_actions(actions, action_context, parse_errors)

        if actions and not message_text:
            await self._emit_hint(
                self.action_config.get("hint_text") or "Thinking...",
                source,
                origin_trace_id=origin_trace_id,
                meta=meta,
            )

        if actions:
            await self._emit_action_plan(
                actions,
                action_context=action_context,
                proposal=envelope,
            )
        if message_text or not actions:
            await self._emit_thought_chunk(
                "",
                source,
                final=True,
                full_thought=message_text,
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

    async def _emit_hint(
        self,
        text: str,
        source: str,
        *,
        origin_trace_id: Optional[str],
        meta: Optional[dict],
    ) -> None:
        if not self.events or not text:
            return
        if origin_trace_id and origin_trace_id == self.state.last_hint_trace_id:
            return
        if origin_trace_id:
            self.state.last_hint_trace_id = origin_trace_id
        payload = {
            "thought": text,
            "source": source,
            "streaming": False,
            "final": True,
            "full_thought": text,
            "route_keep": True,
        }
        if origin_trace_id is not None:
            payload["origin_trace_id"] = origin_trace_id
        if isinstance(meta, dict) and meta:
            payload["meta"] = meta
        await self.events.emit(
            EventNames.COGNITION_THOUGHT,
            payload=payload,
        )

    def _build_action_context(
        self,
        *,
        origin_trace_id: Optional[str],
        user_input: Optional[str],
        meta: Optional[dict],
        action_hops: int,
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "origin_trace_id": origin_trace_id,
            "user_input": user_input,
            "action_hops": action_hops,
        }
        if isinstance(meta, dict) and meta:
            context["meta"] = meta
        return context

    def _extract_action_context(self, data: Any) -> Dict[str, Any]:
        if isinstance(data, dict):
            context = data.get("context") or {}
            if not context and any(k in data for k in ("origin_trace_id", "user_input", "action_hops")):
                context = {
                    "origin_trace_id": data.get("origin_trace_id"),
                    "user_input": data.get("user_input"),
                    "action_hops": data.get("action_hops", 0),
                }
            if isinstance(context, dict):
                return context
        return {}

    def _limit_actions(
        self,
        actions: List[Dict[str, Any]],
        action_context: Dict[str, Any],
        parse_errors: List[str],
    ) -> List[Dict[str, Any]]:
        if not self.action_config.get("enabled", True):
            return []
        max_hops = int(self.action_config.get("max_action_hops", 3))
        hops = int(action_context.get("action_hops", 0))
        if actions and hops >= max_hops:
            parse_errors.append("action_hops_exceeded")
            return []
        return actions

    async def _emit_action_plan(
        self,
        actions: List[Dict[str, Any]],
        *,
        action_context: Dict[str, Any],
        proposal: Dict[str, Any],
    ) -> None:
        if not self.events or not actions:
            return
        payload = {
            "actions": actions,
            "context": action_context,
            "proposal": proposal,
        }
        origin = action_context.get("origin_trace_id")
        signal = Signal(source=self.name, data=payload, parent_id=origin)
        await self.events.emit(EventNames.ACTION_PLAN, payload=signal)

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

    async def think(
        self,
        input_content: Union[str, list],
        *,
        stream: Optional[bool] = None,
        use_async: Optional[bool] = None,
    ) -> str:
        """Produce a thought using the Brain.

        Args:
            input_content: Plain text string or a list of litellm content
                blocks (for multimodal input with images).
        """
        if self.brain is not None:
            try:
                if stream is None:
                    stream = False
                    if hasattr(self.brain, "config") and self.brain.config:
                        stream = getattr(self.brain.config, "llm_stream", False)
                if use_async is None:
                    use_async = False
                    if hasattr(self.brain, "config") and self.brain.config:
                        use_async = getattr(self.brain.config, "llm_use_async", False)

                messages = [{"role": "user", "content": input_content}]
                response_parts = []
                async for chunk in self.brain.think(messages, stream=bool(stream), use_async=bool(use_async)):
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

    async def handle_action_result(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """Handle action results and generate a follow-up response."""
        if not isinstance(signal.data, dict):
            return None

        data = signal.data
        context = self._extract_action_context(data)
        origin_trace_id = context.get("origin_trace_id") or signal.parent_id
        user_input = context.get("user_input")
        action_hops = int(context.get("action_hops", 0)) + 1

        action_results = data.get("action_results") or data.get("result") or data
        prompt = self._format_action_result_prompt(user_input, action_results)

        thought = await self.think(prompt)
        envelope, parse_errors = parse_action_envelope(thought)
        message_text = envelope.get("message") or ""
        actions = envelope.get("actions") or []

        action_context = self._build_action_context(
            origin_trace_id=origin_trace_id,
            user_input=user_input,
            meta=context.get("meta"),
            action_hops=action_hops,
        )
        actions = self._limit_actions(actions, action_context, parse_errors)

        if not message_text:
            message_text = self._fallback_action_result_text(action_results)

        self.state.add_turn("user", prompt)
        self.state.add_turn("assistant", message_text or thought)
        self.state.last_thought = message_text or thought

        return {
            "thought": message_text,
            "full_thought": message_text,
            "raw_output": thought,
            "action_proposal": envelope,
            "actions": actions,
            "action_context": action_context,
            "origin_trace_id": origin_trace_id,
            "source": signal.source,
            "streaming": False,
            "final": True,
            "parse_errors": parse_errors,
        }

    @staticmethod
    def _format_action_result_prompt(user_input: Optional[str], action_results: Any) -> str:
        """Format action results into a prompt for follow-up reasoning."""
        user_block = user_input or ""
        try:
            result_block = json.dumps(action_results, ensure_ascii=False, indent=2)
        except Exception:
            result_block = str(action_results)
        return (
            "You executed the following actions for the user. "
            "Summarize the results and provide the best response.\n\n"
            f"User request:\n{user_block}\n\n"
            f"Action results:\n{result_block}\n"
        )

    @staticmethod
    def _fallback_action_result_text(action_results: Any) -> str:
        """Fallback message when LLM returns no message."""
        try:
            result_block = json.dumps(action_results, ensure_ascii=False, indent=2)
        except Exception:
            result_block = str(action_results)
        return f"Action completed.\n{result_block}"

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
            last_hint_trace_id=parsed.get("last_hint_trace_id"),
        )
