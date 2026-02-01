"""
EmotionNeuron: Single PAD-based emotion neuron.

This neuron maintains a compact PAD (Pleasure/Arousal/Dominance) state,
updates it from incoming signals, and provides a lightweight mapping to
discrete emotion labels for downstream consumption.

Event Flow:
    perception.output -> EmotionNeuron -> emotion.changed
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from aeiva.neuron import BaseNeuron, Signal, NeuronConfig
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig

if TYPE_CHECKING:
    from aeiva.event.event_bus import EventBus

logger = logging.getLogger(__name__)


DEFAULT_INPUT_EVENTS = [
    "perception.output",
    "action.result",
    "cognition.thought",
    "emotion.query",
    "emotion.regulate",
    "emotion.update",
]

DEFAULT_SYSTEM_PROMPT = (
    "You are the emotion module for an AI agent (not the user). "
    "Given the conversation context and the current PAD state, decide if the "
    "agent's emotion should change. "
    "Return ONLY a JSON object with keys: "
    "\"update\" (true/false) and \"pad\" (object with pleasure, arousal, dominance in [-1,1]) "
    "when update is true. "
    "If no change is needed, return {\"update\": false}. "
    "Most messages should NOT update emotion; only update on clear, meaningful shifts. "
    "Routine Q/A, acknowledgements, and neutral exchanges should return update=false. "
    "If the context contains explicit emotion or strong affect, update accordingly. "
    "If update=true, ensure the new PAD differs from current by at least the given threshold. "
    "No markdown, no code fences, no extra text."
)


def _default_label_map() -> Dict[str, Dict[str, float]]:
    return {
        "neutral": {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.0},
        "joy": {"pleasure": 0.8, "arousal": 0.6, "dominance": 0.3},
        "calm": {"pleasure": 0.6, "arousal": -0.4, "dominance": 0.2},
        "sadness": {"pleasure": -0.7, "arousal": -0.4, "dominance": -0.2},
        "anger": {"pleasure": -0.6, "arousal": 0.7, "dominance": 0.5},
        "fear": {"pleasure": -0.6, "arousal": 0.7, "dominance": -0.5},
        "surprise": {"pleasure": 0.1, "arousal": 0.9, "dominance": 0.0},
    }


@dataclass
class PADState:
    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "pleasure": self.pleasure,
            "arousal": self.arousal,
            "dominance": self.dominance,
        }


@dataclass
class EmotionNeuronConfig(NeuronConfig):
    """Configuration for EmotionNeuron (PAD-only)."""
    input_events: List[str] = field(default_factory=lambda: DEFAULT_INPUT_EVENTS.copy())
    output_event: str = "emotion.changed"
    sensitivity: float = 0.3
    emit_threshold: float = 0.1
    decay_rate: float = 0.1
    default_pleasure: float = 0.0
    default_arousal: float = 0.0
    default_dominance: float = 0.0
    label_threshold: float = 0.4
    dominance_threshold: float = 0.2
    label_map: Dict[str, Dict[str, float]] = field(default_factory=_default_label_map)
    regulation_step: float = 0.1
    llm_gateway_config: Dict[str, Any] = field(default_factory=dict)
    decision_temperature: float = 0.2
    decision_max_chars: int = 4000
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class EmotionNeuron(BaseNeuron):
    """Single PAD-based emotion neuron with optional discrete label mapping."""

    EMISSIONS = ["emotion.changed"]
    CONFIG_CLASS = EmotionNeuronConfig

    def __init__(
        self,
        name: str = "emotion",
        config: Dict = None,
        event_bus: "EventBus" = None,
        **kwargs
    ):
        cfg = config or {}
        neuron_config = EmotionNeuronConfig(
            input_events=cfg.get("input_events", DEFAULT_INPUT_EVENTS.copy()),
            output_event=cfg.get("output_event", "emotion.changed"),
            sensitivity=cfg.get("sensitivity", 0.3),
            emit_threshold=cfg.get("emit_threshold", 0.1),
            decay_rate=cfg.get("decay_rate", 0.1),
            default_pleasure=cfg.get("default_pleasure", 0.0),
            default_arousal=cfg.get("default_arousal", 0.0),
            default_dominance=cfg.get("default_dominance", 0.0),
            label_threshold=cfg.get("label_threshold", 0.4),
            dominance_threshold=cfg.get("dominance_threshold", 0.2),
            label_map=cfg.get("label_map", _default_label_map()),
            llm_gateway_config=cfg.get("llm_gateway_config", {}),
            decision_temperature=cfg.get("decision_temperature", 0.2),
            decision_max_chars=cfg.get("decision_max_chars", 4000),
            system_prompt=cfg.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
        )
        super().__init__(name=name, config=neuron_config, event_bus=event_bus, **kwargs)

        self.SUBSCRIPTIONS = self.config.input_events.copy()
        self.state = PADState(
            pleasure=self.config.default_pleasure,
            arousal=self.config.default_arousal,
            dominance=self.config.default_dominance,
        )
        self.emotions_processed = 0
        self.skipped = 0
        self._llm_client: Optional[LLMClient] = None
        self._last_user_input: Optional[str] = None

    async def setup(self) -> None:
        """Initialize the emotion neuron and its model."""
        await super().setup()
        try:
            self._llm_client = self._build_llm_client(self.config.llm_gateway_config)
        except Exception as exc:
            logger.warning("EmotionNeuron LLM disabled (init failed): %s", exc)
            self._llm_client = None
        logger.info(f"{self.name} setup complete (PAD)")

    def create_event_callback(self, pattern: str):
        async def on_event(event: "Event") -> None:
            if not self.accepting:
                return
            payload = event.payload
            if isinstance(payload, dict) and payload.get("streaming") and not payload.get("final"):
                return
            if isinstance(payload, Signal):
                data = payload.data
                if isinstance(data, dict) and data.get("streaming") and not data.get("final"):
                    return
            signal = self.event_to_signal(event)
            await self.enqueue(signal)

        on_event.__name__ = f"{self.name}_on_{pattern.replace('*', 'any').replace('.', '_')}"
        return on_event

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """Process incoming signal and update emotional state."""
        source = signal.source

        if "emotion.query" in source:
            return self.handle_query(signal)
        if "emotion.regulate" in source:
            return await self.handle_regulate(signal)
        if "emotion.update" in source:
            return await self.handle_update(signal)
        if source.startswith("perception"):
            text = self._extract_text(signal.data)
            if text:
                self._last_user_input = text
            return None
        if not self.is_relevant(signal):
            self.skipped += 1
            return None

        return await self.process_emotion(signal)

    def is_relevant(self, signal: Signal) -> bool:
        """Determine if a signal is emotionally relevant."""
        data = signal.data
        source = signal.source

        if any(s in source for s in ["perception", "action", "cognition"]):
            return True

        if isinstance(data, dict):
            if any(k in data for k in ["emotion", "emotion_label", "sentiment", "valence", "pleasure", "arousal"]):
                return True

        return False

    async def process_emotion(self, signal: Signal) -> Optional[Dict[str, Any]]:
        """Process a signal for emotional impact."""
        update = await self._llm_decide_update(signal)
        if not update:
            return None
        old_state = self.state.to_dict()
        new_state = update.to_dict()
        if self._is_no_change(old_state, new_state):
            return None
        self.state = update
        self.emotions_processed += 1
        return {
            "state": self.state.to_dict(),
            "label": self.label_from_state(),
            "expression": self.express(),
            "source": signal.source,
        }

    async def _llm_decide_update(self, signal: Signal) -> Optional[PADState]:
        if not self._llm_client:
            return None
        text = self._compose_context(signal)
        if not text:
            return None
        content = text.strip()
        max_chars = self.config.decision_max_chars
        if max_chars and len(content) > max_chars:
            content = content[-max_chars:]
        messages = self._build_messages(content, signal)
        try:
            response = await self._llm_client.agenerate(messages)
        except Exception as exc:
            logger.warning("Emotion LLM call failed: %s", exc)
            return None
        return self._parse_llm_response(response)

    def _build_messages(self, text: str, signal: Signal) -> List[Dict[str, str]]:
        state = self.state.to_dict()
        header = (
            f"Source: {signal.source}\n"
            f"Current PAD: p={state['pleasure']:.2f}, a={state['arousal']:.2f}, d={state['dominance']:.2f}\n"
            f"Current label: {self.label_from_state()}\n"
            f"Update threshold (sum abs delta): {self.config.emit_threshold:.2f}"
        )
        return [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": f"{header}\n\nContext:\n{text}"},
        ]

    def _compose_context(self, signal: Signal) -> Optional[str]:
        data = signal.data
        if isinstance(data, dict):
            user_input = data.get("input") or data.get("user_input")
            assistant = data.get("full_thought") or data.get("thought") or data.get("output")
            if user_input and assistant:
                self._last_user_input = None
                return f"User: {user_input}\nAssistant: {assistant}"
        text = self._extract_text(data)
        if not text:
            return None
        if signal.source.startswith("cognition") and self._last_user_input:
            context = f"User: {self._last_user_input}\nAssistant: {text}"
            self._last_user_input = None
            return context
        return text

    def _parse_llm_response(self, response: str) -> Optional[PADState]:
        if not response:
            return None
        text = response.strip()
        data = self._parse_json_object(text)
        if data is None:
            logger.warning("Emotion LLM returned non-JSON response")
            return None
        if not isinstance(data, dict):
            return None
        update_flag = data.get("update", False)
        if isinstance(update_flag, str):
            update_flag = update_flag.strip().lower() in {"true", "yes", "1"}
        if not bool(update_flag):
            return None
        pad = data.get("pad")
        if not isinstance(pad, dict):
            pad = {
                "pleasure": data.get("pleasure"),
                "arousal": data.get("arousal"),
                "dominance": data.get("dominance"),
            }
        if not isinstance(pad, dict):
            return None
        try:
            pleasure = self._clamp(float(pad.get("pleasure")))
            arousal = self._clamp(float(pad.get("arousal")))
            dominance = self._clamp(float(pad.get("dominance")))
        except (TypeError, ValueError):
            return None
        return PADState(pleasure=pleasure, arousal=arousal, dominance=dominance)

    @staticmethod
    def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                import ast
                parsed = ast.literal_eval(text)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None

    def _extract_text(self, data: Any) -> Optional[str]:
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            if data.get("streaming") and not data.get("final"):
                return None
            if data.get("final") and isinstance(data.get("full_thought"), str):
                return data.get("full_thought")
            for key in ("text", "content", "data", "thought", "output"):
                if key in data and isinstance(data[key], str):
                    return data[key]
        if hasattr(data, "data"):
            return self._extract_text(getattr(data, "data"))
        if hasattr(data, "signals"):
            chunks: List[str] = []
            for item in getattr(data, "signals", []) or []:
                text = self._extract_text(item)
                if text:
                    chunks.append(text)
            return " ".join(chunks) if chunks else None
        return None

    def _build_llm_client(self, cfg: Dict[str, Any]) -> LLMClient:
        llm_api_key = cfg.get("llm_api_key")
        if not llm_api_key:
            env_var = cfg.get("llm_api_key_env_var")
            if env_var:
                llm_api_key = os.getenv(env_var)
        valid_keys = LLMGatewayConfig.__dataclass_fields__.keys()
        params = {k: v for k, v in cfg.items() if k in valid_keys}
        params["llm_api_key"] = llm_api_key
        params["llm_temperature"] = self.config.decision_temperature
        params["llm_use_async"] = True
        params["llm_stream"] = False
        return LLMClient(LLMGatewayConfig(**params))

    def is_significant_change(self, old_state: Dict[str, float], new_state: Dict[str, float]) -> bool:
        """Check if state change is significant enough to emit."""
        total_change = sum(
            abs(new_state[k] - old_state[k])
            for k in new_state
            if k in old_state
        )
        return total_change >= self.config.emit_threshold

    @staticmethod
    def _is_no_change(old_state: Dict[str, float], new_state: Dict[str, float]) -> bool:
        for key in ("pleasure", "arousal", "dominance"):
            if abs(float(new_state.get(key, 0.0)) - float(old_state.get(key, 0.0))) >= 1e-3:
                return False
        return True

    def handle_query(self, signal: Signal) -> Dict[str, Any]:
        """Handle emotion state query requests."""
        data = signal.data if isinstance(signal.data, dict) else {}
        query_type = data.get("type", "state")
        show = bool(data.get("show", False))
        origin = data.get("origin")

        if query_type == "state":
            result = {
                "type": "state",
                "state": self.state.to_dict(),
                "label": self.label_from_state(),
                "expression": self.express(),
            }
            if show:
                result["show"] = True
            if origin:
                result["origin"] = origin
            return result
        elif query_type == "expression":
            result = {
                "type": "expression",
                "expression": self.express(),
            }
            if show:
                result["show"] = True
            if origin:
                result["origin"] = origin
            return result
        else:
            return {"type": "error", "message": f"Unknown query type: {query_type}"}

    async def handle_regulate(self, signal: Signal) -> Dict[str, Any]:
        """Handle emotion regulation requests."""
        data = signal.data if isinstance(signal.data, dict) else {}
        strategy = data.get("strategy", "decay")
        amount = data.get("amount")

        self.regulate(strategy, amount)
        return {
            "type": "regulated",
            "strategy": strategy,
            "state": self.state.to_dict(),
            "label": self.label_from_state(),
            "expression": self.express(),
        }

    async def handle_update(self, signal: Signal) -> Dict[str, Any]:
        """Handle direct emotion update requests."""
        data = signal.data if isinstance(signal.data, dict) else {}

        if any(k in data for k in ["pleasure", "arousal", "dominance"]):
            self.state.pleasure = self._clamp(float(data.get("pleasure", self.state.pleasure)))
            self.state.arousal = self._clamp(float(data.get("arousal", self.state.arousal)))
            self.state.dominance = self._clamp(float(data.get("dominance", self.state.dominance)))

        return {
            "type": "updated",
            "state": self.state.to_dict(),
            "label": self.label_from_state(),
            "expression": self.express(),
        }

    async def send(self, output: Any, parent: Signal = None) -> None:
        """Send emotion event."""
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
        health["model"] = "pad"
        health["emotions_processed"] = self.emotions_processed
        health["current_expression"] = self.express()
        health["state"] = self.state.to_dict()
        return health

    def serialize(self) -> str:
        """Serialize state."""
        return json.dumps(self.state.to_dict())

    def deserialize(self, data: str) -> None:
        """Deserialize state."""
        try:
            payload = json.loads(data)
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        self.state.pleasure = self._clamp(float(payload.get("pleasure", self.state.pleasure)))
        self.state.arousal = self._clamp(float(payload.get("arousal", self.state.arousal)))
        self.state.dominance = self._clamp(float(payload.get("dominance", self.state.dominance)))

    def regulate(self, strategy: str, amount: Optional[float] = None) -> None:
        step = float(amount) if amount is not None else self.config.regulation_step
        step = max(0.0, min(step, 1.0))

        if strategy in ("neutralize", "reset"):
            self.state.pleasure = self.config.default_pleasure
            self.state.arousal = self.config.default_arousal
            self.state.dominance = self.config.default_dominance
            return

        if strategy == "decay":
            self.apply_decay()
            return

        if strategy == "increase":
            factor = 1.0 + step
        elif strategy == "decrease":
            factor = 1.0 - step
        else:
            return

        self.state.pleasure = self._clamp(self.state.pleasure * factor)
        self.state.arousal = self._clamp(self.state.arousal * factor)
        self.state.dominance = self._clamp(self.state.dominance * factor)

    def apply_decay(self) -> None:
        factor = 1.0 - max(0.0, min(self.config.decay_rate, 1.0))
        self.state.pleasure *= factor
        self.state.arousal *= factor
        self.state.dominance *= factor

    def apply_impact(self, impact: Dict[str, float]) -> None:
        self.state.pleasure = self._clamp(self.state.pleasure + float(impact.get("pleasure", 0.0)))
        self.state.arousal = self._clamp(self.state.arousal + float(impact.get("arousal", 0.0)))
        self.state.dominance = self._clamp(self.state.dominance + float(impact.get("dominance", 0.0)))

    def impact_from_label(self, label: str, intensity: float) -> Optional[Dict[str, float]]:
        target = self.config.label_map.get(label)
        if not target:
            return None
        return {
            "pleasure": (target.get("pleasure", 0.0) - self.state.pleasure) * intensity,
            "arousal": (target.get("arousal", 0.0) - self.state.arousal) * intensity,
            "dominance": (target.get("dominance", 0.0) - self.state.dominance) * intensity,
        }

    def label_from_state(self) -> str:
        v = self.state.pleasure
        a = self.state.arousal
        d = self.state.dominance
        t = self.config.label_threshold
        d_t = self.config.dominance_threshold

        if abs(v) < t and abs(a) < t:
            return "neutral"
        if v >= t and a >= t:
            return "joy"
        if v >= t and a <= -t:
            return "calm"
        if v <= -t and a <= -t:
            return "sadness"
        if v <= -t and a >= t:
            return "anger" if d >= d_t else "fear"
        if a >= t:
            return "alert"
        if a <= -t:
            return "tired"
        return "neutral"

    def express(self) -> str:
        label = self.label_from_state()
        return (
            f"{label} (p={self.state.pleasure:.2f}, "
            f"a={self.state.arousal:.2f}, d={self.state.dominance:.2f})"
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(-1.0, min(1.0, value))
